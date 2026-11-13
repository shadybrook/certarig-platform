"""OIDC identity only. Model authentication and equipment authority remain separate."""

from __future__ import annotations

import os
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit

from .store import Store, sha

_transport_lock = threading.RLock()


@contextmanager
def transport(issuer: str) -> Iterator[None]:
    # OAuthlib documents this development exception. Keep it scoped to a verified
    # loopback issuer and restore the process setting before any other login.
    with _transport_lock:
        previous = os.environ.get("OAUTHLIB_INSECURE_TRANSPORT")
        try:
            if issuer.startswith("http://127.0.0.1:") or issuer.startswith("http://localhost:"):
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            yield
        finally:
            if previous is None:
                os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)
            else:
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = previous


class OIDC:
    def __init__(
        self, store: Store, issuer: str, client_id: str, callback: str, client_secret: str | None = None
    ):
        self.store, self.issuer, self.client_id = store, issuer.rstrip("/"), client_id
        self.callback, self.client_secret = callback, client_secret
        for url in [self.issuer, callback]:
            parsed = urlsplit(url)
            if (
                parsed.username
                or parsed.password
                or (
                    parsed.scheme != "https"
                    and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"})
                )
            ):
                raise ValueError("OIDC requires HTTPS except for loopback development")
        self._metadata: dict[str, Any] | None = None

    def metadata(self) -> dict[str, Any]:
        import requests

        if self._metadata is None:
            response = requests.get(self.issuer + "/.well-known/openid-configuration", timeout=5)
            response.raise_for_status()
            data = response.json()
            if data["issuer"] != self.issuer:
                raise ValueError("OIDC discovery issuer mismatch")
            # Endpoints cannot silently downgrade TLS or redirect to another host.
            for key in ["authorization_endpoint", "token_endpoint", "jwks_uri"]:
                p, expected = urlsplit(data[key]), urlsplit(self.issuer)
                if (p.scheme, p.netloc) != (expected.scheme, expected.netloc):
                    raise ValueError("Unexpected OIDC endpoint origin")
            self._metadata = data
        return self._metadata

    def start(self) -> tuple[str, str]:
        with transport(self.issuer):
            return self._start()

    def _start(self) -> tuple[str, str]:
        from requests_oauthlib import OAuth2Session

        state, browser, nonce = (secrets.token_urlsafe(32) for _ in range(3))
        client = OAuth2Session(
            self.client_id,
            redirect_uri=self.callback,
            scope=["openid", "profile", "email"],
            state=state,
            pkce="S256",
        )
        url, _ = client.authorization_url(self.metadata()["authorization_endpoint"], nonce=nonce)
        self.store.transaction(
            "oidc", state, {"browser": sha(browser), "nonce": nonce, "verifier": client._code_verifier}
        )
        return url, browser

    def finish(self, state: str, code: str, browser: str) -> tuple[str, dict[str, Any]]:
        with transport(self.issuer):
            return self._finish(state, code, browser)

    def _finish(self, state: str, code: str, browser: str) -> tuple[str, dict[str, Any]]:
        import jwt
        from requests_oauthlib import OAuth2Session

        tx = self.store.consume("oidc", state)
        if not secrets.compare_digest(tx["browser"], sha(browser)):
            raise PermissionError("Login transaction belongs to another browser")
        client = OAuth2Session(self.client_id, redirect_uri=self.callback, state=state, pkce="S256")
        client._code_verifier = tx["verifier"]
        token = client.fetch_token(
            self.metadata()["token_endpoint"],
            code=code,
            code_verifier=tx["verifier"],
            client_secret=self.client_secret,
            include_client_id=True,
            timeout=5,
        )
        key = jwt.PyJWKClient(self.metadata()["jwks_uri"], timeout=5).get_signing_key_from_jwt(
            token["id_token"]
        )
        claims = jwt.decode(
            token["id_token"],
            key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "nonce"]},
        )
        if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != self.client_id:
            raise PermissionError("OIDC authorized party mismatch")
        if not secrets.compare_digest(claims["nonce"], tx["nonce"]):
            raise PermissionError("OIDC nonce mismatch")
        return self.store.login(self.issuer, str(claims["sub"]))
