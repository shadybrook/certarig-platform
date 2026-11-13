"""Real signed OIDC exchanges against an explicit test issuer, plus HTTP authorization tests."""

import base64
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from certarig.platform.auth import OIDC, transport
from certarig.platform.client import PlatformClient
from certarig.platform.server import API, server
from certarig.platform.store import Store

from .test_lifecycle import FixtureProvider


@pytest.fixture
def issuer():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public.update(kid="test-key", alg="RS256", use="sig")
    state = {"claims": {}, "nonce": "", "challenge": "", "metadata": {}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.endswith("/keys"):
                data = {"keys": [public]}
            else:
                data = {
                    "issuer": origin,
                    "authorization_endpoint": origin + "/auth",
                    "token_endpoint": origin + "/token",
                    "jwks_uri": origin + "/keys",
                    **state["metadata"],
                }
            payload = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            data = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"][0].encode()).digest())
                .decode()
                .rstrip("=")
            )
            if data["code"][0] != "single-code" or challenge != state["challenge"]:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":"invalid_grant"}')
                return
            claims = {
                "iss": origin,
                "aud": "certarig-test",
                "sub": "author",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
                "nonce": state["nonce"],
                **state["claims"],
            }
            token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})
            payload = json.dumps(
                {"access_token": "test-only", "token_type": "Bearer", "id_token": token, "expires_in": 300}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = "http://127.0.0.1:" + str(http.server_port)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    yield origin, state
    http.shutdown()
    http.server_close()
    thread.join()


def start(oidc, state):
    url, browser = oidc.start()
    q = parse_qs(urlsplit(url).query)
    assert q["code_challenge_method"] == ["S256"]
    state["nonce"], state["challenge"] = q["nonce"][0], q["code_challenge"][0]
    return q["state"][0], browser


def test_real_oidc_signature_pkce_sessions_nonce_and_replay(tmp_path, issuer):
    origin, state = issuer
    store = Store(tmp_path / "oidc")
    try:
        user = store.provision(origin, "author", "org", "author")
        reviewer = store.provision(origin, "reviewer", "org", "reviewer")
        oidc = OIDC(store, origin, "certarig-test", "http://127.0.0.1:18090/v1/auth/callback")
        tx, browser = start(oidc, state)
        token, _ = oidc.finish(tx, "single-code", browser)
        assert store.session(token)[0].user_id == user
        with pytest.raises(ValueError):
            oidc.finish(tx, "single-code", browser)
        state["claims"] = {"sub": "reviewer"}
        tx, browser = start(oidc, state)
        token2, _ = oidc.finish(tx, "single-code", browser)
        assert store.session(token2)[0].user_id == reviewer
        assert store.session(token2)[0].role == "reviewer"
        tx, browser = start(oidc, state)
        with pytest.raises(PermissionError):
            oidc.finish(tx, "single-code", "another-browser")
        for overrides, error in [
            ({"nonce": "forged"}, PermissionError),
            ({"iss": origin + "/forged"}, jwt.InvalidIssuerError),
            ({"aud": "forged"}, jwt.InvalidAudienceError),
            ({"exp": 1}, jwt.ExpiredSignatureError),
            ({"aud": ["certarig-test", "other"], "azp": "other"}, PermissionError),
        ]:
            state["claims"] = overrides
            tx, browser = start(oidc, state)
            with pytest.raises(error):
                oidc.finish(tx, "single-code", browser)
        state["claims"] = {}
        tx, browser = start(oidc, state)
        with pytest.raises(Exception, match="invalid_grant"):
            oidc.finish(tx, "bad-code", browser)
    finally:
        store.close()


def test_oidc_discovery_origins_and_transport_rejects_downgrades(tmp_path, issuer, monkeypatch):
    s = Store(tmp_path / "oidc")
    origin, state = issuer
    try:
        for bad in ["http://example.com", "file:///tmp/id", "https://user:pass@example.com"]:
            with pytest.raises(ValueError):
                OIDC(s, bad, "client", "http://127.0.0.1:18090/callback")
        state["metadata"] = {"issuer": "wrong"}
        with pytest.raises(ValueError):
            OIDC(s, origin, "client", "http://127.0.0.1:18090/callback").metadata()
        state["metadata"] = {"jwks_uri": "http://elsewhere/keys"}
        with pytest.raises(ValueError):
            OIDC(s, origin, "client", "http://127.0.0.1:18090/callback").metadata()
        monkeypatch.setenv("OAUTHLIB_INSECURE_TRANSPORT", "previous")
        with transport(origin):
            assert __import__("os").environ["OAUTHLIB_INSECURE_TRANSPORT"] == "1"
        assert __import__("os").environ["OAUTHLIB_INSECURE_TRANSPORT"] == "previous"
    finally:
        s.close()


class Login:
    def __init__(self, store):
        self.store = store

    def start(self):
        return "http://127.0.0.1/test-issuer", "test-browser"

    def finish(self, state, code, browser):
        if browser != "test-browser":
            raise PermissionError("Wrong browser")
        return self.store.login("issuer", code)


@pytest.fixture
def http(lab):
    api = API(lab.p, Login(lab.store), lab.broker, lambda c: FixtureProvider())
    endpoint = server(api, 0, __import__("pathlib").Path(__file__).resolve().parents[2] / "studio")
    thread = threading.Thread(target=endpoint.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(endpoint.server_port)
    yield origin, api
    endpoint.shutdown()
    endpoint.server_close()
    thread.join()
    api.close()


def test_http_cookie_auth_csrf_role_and_scoped_downloads(lab, http):
    origin, api = http
    assert requests.get(origin + "/v1/auth/me").status_code == 401
    assert (
        requests.get(
            origin + "/v1/assets", headers={"X-CertaRig-Operator-Key": "forged", "X-Role": "reviewer"}
        ).status_code
        == 401
    )
    browser = requests.Session()
    response = browser.get(origin + "/v1/auth/login", allow_redirects=False)
    assert response.status_code == 302 and "HttpOnly" in response.headers["Set-Cookie"]
    response = browser.get(origin + "/v1/auth/callback?state=test&code=author", allow_redirects=False)
    assert response.status_code == 302 and "HttpOnly" in response.headers["Set-Cookie"]
    me = browser.get(origin + "/v1/auth/me").json()
    assert me["user_id"] == lab.author.user_id
    headers = {"Origin": origin, "X-CSRF-Token": me["csrf"]}
    assert browser.post(origin + "/v1/agents", json=lab.body).status_code == 403
    assert (
        browser.post(
            origin + "/v1/agents", json=lab.body, headers={**headers, "Origin": "https://attacker.test"}
        ).status_code
        == 403
    )
    assert (
        browser.post(origin + "/v1/assets/pair", json={"connector": "a"}, headers=headers).status_code == 403
    )
    assert browser.get(origin + "/v1/assets/" + lab.b["id"] + "/signals").status_code == 404
    assert browser.get(origin + "/v1/auth/members").status_code == 403
    assert browser.get(origin + "/v1/agents/evaluations").json() == {"evaluations": []}
    assert browser.get(origin + "/v1/agents/preflight").json()["ready"]
    assert browser.get(origin + "/v1/deployments").json() == {"deployments": []}
    response = browser.post(origin + "/v1/agents", json=lab.body, headers=headers)
    assert response.status_code == 200 and response.json()["author_id"] == lab.author.user_id
    assert browser.get(origin + "/v1/no-such-resource").status_code == 404
    assert browser.get(origin + "/v1/auth/me", headers={"Host": "evil.test"}).status_code == 401
    client = PlatformClient(origin, browser.cookies["certarig_session"], me["csrf"])
    assert client.me()["role"] == "author"
    assert client.create_agent(**lab.body)["revision"] == 1
    with pytest.raises(ValueError):
        PlatformClient("http://example.com", "token")
    with pytest.raises(ValueError):
        client.request("GET", "/file")
    assert browser.post(origin + "/v1/auth/logout", json={}, headers=headers).status_code == 200
    assert browser.get(origin + "/v1/auth/me").status_code == 401


def test_http_full_fixture_review_and_export(lab, http):
    origin, api = http
    author_token, author_info = lab.store.login("issuer", "author")
    author = PlatformClient(origin, author_token, author_info["csrf"])
    e = author.request("POST", "/v1/agents/" + lab.v["id"] + "/evaluate", {})
    assert e["status"] == "awaiting_sandbox"
    e = author.request("POST", "/v1/agents/evaluations/" + e["id"], {})
    assert author.request("GET", "/v1/agents/evaluations/" + e["id"])["trusted"]
    token, info = lab.store.login("issuer", "reviewer")
    reviewer = PlatformClient(origin, token, info["csrf"])
    assert reviewer.request("GET", "/v1/auth/members")["members"]
    assert reviewer.request("GET", "/v1/assets/" + lab.a["id"] + "/signals")["fixture"]
    d = reviewer.request(
        "POST", "/v1/deployments/review", {"version_id": lab.v["id"], "evaluation_id": e["id"]}
    )
    assert reviewer.request("GET", "/v1/deployments/" + d["id"])["status"] == "approved"
    d = reviewer.request("POST", "/v1/deployments/" + d["id"] + "/start", {})
    assert d["status"] == "running"
    assert reviewer.request("GET", "/v1/deployments/" + d["id"] + "/events")["events"]
    assert author.request("GET", "/v1/deployments/" + d["id"] + "/export").startswith(b"PK")
    assert author.revoke(d["id"])["status"] == "revoked"
    assert (
        reviewer.request(
            "POST", "/v1/assets/" + lab.a["id"] + "/grants", {"user_id": lab.author.user_id, "enabled": False}
        )["enabled"]
        is False
    )
    conn = reviewer.request(
        "POST", "/v1/model-connections", {"backend": "fixture", "model": "deterministic/1", "consent": False}
    )
    assert (
        reviewer.request("POST", "/v1/model-connections/" + conn["id"] + "/disconnect", {})["status"]
        == "disconnected"
    )


def test_http_static_contract_invalid_bodies_and_managed_account_scoping(lab, http):
    origin, api = http
    for path, kind in [
        ("/", "text/html"),
        ("/styles.css", "text/css"),
        ("/platform.css", "text/css"),
        ("/src/platform.mjs", "javascript"),
    ]:
        r = requests.get(origin + path)
        assert r.status_code == 200 and kind in r.headers["Content-Type"]
        assert (
            r.headers["X-Content-Type-Options"] == "nosniff"
            and "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
        )
    assert requests.get(origin + "/../pyproject.toml").status_code == 404
    token, info = lab.store.login("issuer", "author")
    headers = {
        "Cookie": "certarig_session=" + token,
        "X-CSRF-Token": info["csrf"],
        "Origin": origin,
        "Content-Type": "application/json",
    }
    assert requests.post(origin + "/v1/agents", data="[]", headers=headers).status_code == 409
    assert (
        requests.post(
            origin + "/v1/agents", data="{}", headers={**headers, "Content-Type": "text/plain"}
        ).status_code
        == 409
    )
    client = PlatformClient(origin, token, info["csrf"])
    doc = client.request("GET", "/v1/openapi.json")
    assert doc["security"] == [{"applicationSession": []}]
    assert "/v1/deployments/{deployment_id}/revoke" in doc["paths"]
    c = client.request(
        "POST", "/v1/model-connections", {"backend": "codex", "model": "test-model", "consent": True}
    )

    class Managed:
        closed = False

        def login(self):
            return {"userCode": "test-only-code", "verificationUrl": "https://auth.openai.com/codex/device"}

        def account(self):
            return {"connected": True}

        def close(self):
            self.closed = True

    managed = Managed()
    api.providers = lambda connection: managed
    assert (
        client.request("POST", "/v1/model-connections/" + c["id"] + "/login", {})["userCode"]
        == "test-only-code"
    )
    assert client.request("POST", "/v1/model-connections/" + c["id"] + "/status", {})["connected"]
    changed = client.request("POST", "/v1/agents/" + lab.v["agent_id"] + "/versions", lab.body)
    assert changed["revision"] == 2
    assert client.request("POST", "/v1/model-connections/" + c["id"] + "/disconnect", {})["enabled"] is False
    assert managed.closed
    # Unknown provider errors are redacted. Role/key headers still cannot change ownership.
    api.providers = lambda connection: (_ for _ in ()).throw(RuntimeError("private diagnostic"))
    c = client.request(
        "POST", "/v1/model-connections", {"backend": "codex", "model": "test-model", "consent": True}
    )
    r = requests.post(origin + "/v1/model-connections/" + c["id"] + "/login", json={}, headers=headers)
    assert r.status_code == 503 and "private diagnostic" not in r.text
