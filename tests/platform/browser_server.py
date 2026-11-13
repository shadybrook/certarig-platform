"""Explicit test-only dependencies for rendered Studio acceptance. Never use for qualification."""

import sys
from pathlib import Path

from certarig.platform.server import API, server
from tests.platform.test_identity_http import Login
from tests.platform.test_lifecycle import FixtureProvider, lab

if __name__ == "__main__":
    context = lab.__wrapped__(Path(sys.argv[1]))
    value = next(context)
    api = API(value.p, Login(value.store), value.broker, lambda c: FixtureProvider())
    http = server(api, 18095, Path(__file__).resolve().parents[2] / "studio")
    print("TEST-ONLY platform ready http://127.0.0.1:18095", flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
        api.close()
        try:
            next(context)
        except StopIteration:
            pass
