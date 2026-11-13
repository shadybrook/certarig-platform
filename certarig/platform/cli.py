"""Local control-plane and separately managed observation-runtime commands."""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import secrets
import threading
from pathlib import Path
from typing import Any

import yaml

from certarig.edge.atomic import write_json_atomic
from certarig.edge.bootstrap import DEFAULT_SKILLS_ROOT, NodeSettings, build_node
from certarig.edge.server import make_edge_server
from certarig.sandbox.transport import BrokerClient

from .auth import OIDC
from .codex import CodexProvider
from .evaluation import FixtureProvider, validate
from .runtime import Runtime
from .server import API, server
from .service import Platform
from .store import Store


def initialize(root: Path, source: Path) -> dict[str, Any]:
    import bcrypt

    s = Store(root)
    try:
        if (root / "settings.json").exists():
            raise ValueError("Local proof is already initialized; existing data was preserved")
        issuer = "http://127.0.0.1:15556/dex"
        accounts, passwords = [], []
        for role in ("author", "reviewer"):
            password = secrets.token_urlsafe(18)
            # Dex v2.45 uses protobuf IDTokenSubject(user_id=1,conn_id=2), raw URL base64.
            subject = (
                base64.urlsafe_b64encode(bytes([10, len(role)]) + role.encode() + b"\x12\x05local")
                .decode()
                .rstrip("=")
            )
            user_id = s.provision(issuer, subject, "certa-lab", role)
            accounts.append(
                {"role": role, "email": role + "@certarig.local", "password": password, "user_id": user_id}
            )
            passwords.append(
                {
                    "email": role + "@certarig.local",
                    "hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                    "username": role.title(),
                    "userID": role,
                }
            )
        configs = {}
        for index, (key, name, filename) in enumerate(
            [
                ("thermal", "Bench A · Thermal", "rig.thermal.capstone.json"),
                ("pressure", "Bench B · Pressure / flow", "rig.sim.json"),
            ]
        ):
            auditor = secrets.token_urlsafe(32)
            configs[key] = {
                "name": name,
                "org_id": "certa-lab",
                "url": "http://127.0.0.1:" + str(18091 + index),
                "auditor_key": auditor,
                "operator_key": secrets.token_urlsafe(32),
                "config": str(source / "config" / filename),
            }
        settings = {
            "issuer": issuer,
            "client_id": "certarig-local",
            "callback": "http://127.0.0.1:18090/v1/auth/callback",
            "connectors": configs,
            "sandbox_socket": str(root / "sandbox" / "broker.sock"),
        }
        s.secret("demo_accounts", {"accounts": accounts})
        s.secret("settings", settings)
        # Public marker contains no connector credentials.
        write_json_atomic(root / "settings.json", {"private_settings": "secrets/settings.json"})
        (root / "settings.json").chmod(0o600)
        dex = {
            "issuer": issuer,
            "storage": {"type": "sqlite3", "config": {"file": str(root / "dex.sqlite")}},
            "web": {"http": "127.0.0.1:15556"},
            "oauth2": {"skipApprovalScreen": True},
            "enablePasswordDB": True,
            "staticClients": [
                {
                    "id": "certarig-local",
                    "name": "CertaRig local proof",
                    "public": True,
                    "redirectURIs": [settings["callback"]],
                }
            ],
            "staticPasswords": passwords,
        }
        path = root / "dex.yaml"
        path.write_text(yaml.safe_dump(dex))
        path.chmod(0o600)
        return {
            "root": str(root),
            "dex_config": str(path),
            "accounts_file": str(root / "secrets" / "demo_accounts.json"),
            "author_id": accounts[0]["user_id"],
            "reviewer_id": accounts[1]["user_id"],
            "qualification": "not_run",
        }
    finally:
        s.close()


def providers(root: Path) -> Any:
    def factory(connection: dict[str, Any]) -> Any:
        if connection["backend"] == "fixture":
            if connection["model"] != "deterministic/1":
                raise ValueError("Fixture model must be deterministic/1")
            return FixtureProvider()
        return CodexProvider(root / "model-profiles" / connection["id"], connection["model"])

    return factory


def run(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    if args.action == "init-demo":
        print(json.dumps(initialize(root, Path(__file__).resolve().parents[2]), indent=2))
        return
    if args.action == "verify":
        from .evidence import verify

        print(json.dumps(verify(Path(args.bundle).read_bytes()), indent=2))
        return
    store = Store(root)
    lock = (root / (args.action + ".lock")).open("a")
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("This local service is already running") from exc
        settings = store.secret("settings")
        if args.action == "demo-edges":
            nodes, servers = [], []
            try:
                for key, config in settings["connectors"].items():
                    n = build_node(
                        NodeSettings(
                            Path(config["config"]),
                            Path(__file__).resolve().parents[2] / "config" / "capabilities.observe.json",
                            root / "edges" / key,
                            None,
                            config["operator_key"],
                            None,
                            config["auditor_key"],
                            False,
                            DEFAULT_SKILLS_ROOT,
                        )
                    )
                    if n.config.hardware.mode != "simulator":
                        n.close()
                        raise ValueError("Demo accepts simulator profiles only")
                    n.private_reads = True
                    endpoint = make_edge_server(n, "127.0.0.1", int(config["url"].rsplit(":", 1)[1]))
                    nodes.append(n)
                    servers.append(endpoint)
                    n.start()
                    threading.Thread(target=endpoint.serve_forever, daemon=True).start()
                print("Two simulator acquisition services started; no physical connectors.", flush=True)
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
            finally:
                for endpoint in servers:
                    endpoint.shutdown()
                    endpoint.server_close()
                for n in nodes:
                    n.close()
            return
        platform = Platform(store, settings["connectors"], recover=args.action == "serve")
        broker = BrokerClient(Path(settings["sandbox_socket"]))
        factory = providers(root)
        if args.action == "runtime":
            runtime = Runtime(platform, factory, lambda a, e: validate(platform, a, e, broker))
            try:
                # A runtime process restart never adopts previously started work.
                for row in store.db.execute("SELECT body FROM documents WHERE kind='deployment'").fetchall():
                    d = json.loads(row[0])
                    if d["status"] == "running":
                        platform.pause(d, "Runtime restarted; independent review required")
                print("Observation runtime ready; no deployments resumed.", flush=True)
                runtime.serve()
            except KeyboardInterrupt:
                pass
            finally:
                runtime.close()
            return
        oidc = OIDC(store, settings["issuer"], settings["client_id"], settings["callback"])
        api = API(platform, oidc, broker, factory)
        endpoint = server(api, 18090, Path(__file__).resolve().parents[2] / "studio")
        print("CertaRig local Studio: http://127.0.0.1:18090", flush=True)
        try:
            endpoint.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            endpoint.server_close()
            api.close()
    finally:
        lock.close()
        store.close()


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("platform", help="local customer-agent proof; no physical deployment")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("init-demo", "serve", "demo-edges", "runtime", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--root", default="~/.local/share/certarig-platform")
        if name == "verify":
            command.add_argument("bundle")
        command.set_defaults(func=run)
