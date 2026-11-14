"""Explicit test-only dependencies for rendered Studio acceptance. Never use for qualification."""

import json
import sys
import threading
from pathlib import Path

from certarig.platform.server import API, server
from tests.platform.test_identity_http import Login
from tests.platform.test_lifecycle import Client, FixtureProvider, lab

if __name__ == "__main__":
    context = lab.__wrapped__(Path(sys.argv[1]))
    value = next(context)
    from tests.platform.test_workbench import AnalysisEngine

    value.broker.engine = AnalysisEngine()
    control = Path(sys.argv[1]) / "ui-controls.json"

    class BrowserClient(Client):
        def rig(self):
            result = super().rig()
            result["rig"] = json.loads(
                (Path(__file__).resolve().parents[2] / "config" / "rig.thermal.sim.json").read_text()
            )
            controls = json.loads(control.read_text()) if control.exists() else {}
            if self.url.endswith(":18091"):
                result["config_hash"] = controls.get("profile", self.profile)
            return result

    value.p.client_factory = BrowserClient
    stop = threading.Event()

    def fixture_controls():
        while not stop.wait(0.05):
            try:
                controls = json.loads(control.read_text()) if control.exists() else {}
                if controls.get("runtime_offline"):
                    value.runtime.close()
                    return
            except (OSError, ValueError):
                pass

    watcher = threading.Thread(target=fixture_controls, daemon=True)
    watcher.start()
    api = API(value.p, Login(value.store), value.broker, lambda c: FixtureProvider())
    http = server(api, 18095, Path(__file__).resolve().parents[2] / "studio")
    print("TEST-ONLY platform ready http://127.0.0.1:18095", flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        watcher.join(timeout=1)
        http.server_close()
        api.close()
        try:
            next(context)
        except StopIteration:
            pass
