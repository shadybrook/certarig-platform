"""Release gate: ONLY this fixed suite may qualify the pinned image.

Default CI skips it. `certarig sandbox qualify` opts in after the resource preflight.
No submitted content is ever executed on the host.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from threading import Event

import pytest

from certarig.sandbox.contracts import encoded, verify_rehearsal
from certarig.sandbox.engine import DockerEngine

pytestmark = [
    pytest.mark.sandbox_runtime,
    pytest.mark.skipif(
        os.environ.get("CERTARIG_SANDBOX_QUALIFY") != "1",
        reason="real-container release gate is opt-in; not qualified by mocked tests",
    ),
]


@pytest.fixture(scope="module")
def runtime():  # type: ignore[no-untyped-def]
    root = Path(os.environ["CERTARIG_SANDBOX_ROOT"])
    engine = DockerEngine((root / "image.id").read_text().strip(), root, qualification_mode=True)
    check = engine.preflight()
    if not check["ready"]:
        pytest.fail("Runtime prerequisites are not satisfied: " + str(check["blockers"]))
    return engine


def run(runtime, source, seconds=15, kind="python", inputs=None):  # type: ignore[no-untyped-def]
    jid = "job_" + secrets.token_hex(8)
    payload = inputs or {"main.py": source.encode()}
    return runtime.run(jid, kind, payload, seconds, Event())


def test_container_isolation(runtime, tmp_path):  # type: ignore[no-untyped-def]
    canary = tmp_path / "private-canary"
    canary.write_text(secrets.token_hex(16))
    os.environ["CR_HOST_CANARY"] = canary.read_text()
    try:
        source = f"""import os,json,socket
from pathlib import Path
results={{'uid':os.getuid(),'host_file':Path({str(canary)!r}).exists(),'credential':os.environ.get('CR_HOST_CANARY'),'docker':Path('/var/run/docker.sock').exists(),'gpio':Path('/dev/gpiomem').exists(),'i2c':Path('/dev/i2c-1').exists()}}
try:
 Path('/app/forbidden.txt').write_text('bad');results['root_readonly']=False
except OSError:results['root_readonly']=True
try:
 socket.create_connection(('1.1.1.1',53),timeout=.2).close();results['network_blocked']=False
except OSError:results['network_blocked']=True
Path('isolation.json').write_text(json.dumps(results))"""
        result = run(runtime, source)
        assert result["status"] == "completed", result
        observed = json.loads(result["files"]["isolation.json"])
        assert observed == {
            "uid": 10001,
            "host_file": False,
            "credential": None,
            "docker": False,
            "gpio": False,
            "i2c": False,
            "root_readonly": True,
            "network_blocked": True,
        }
    finally:
        os.environ.pop("CR_HOST_CANARY", None)


def test_infinite_loop_deadline(runtime):  # type: ignore[no-untyped-def]
    result = run(runtime, "while True: pass", seconds=2)
    assert result["status"] in {"timed_out", "failed"}
    assert result["resource"]["elapsed_s"] < 15


def test_memory_limit(runtime):  # type: ignore[no-untyped-def]
    result = run(runtime, "data=[bytearray(64*1024**2) for _ in range(100)]", seconds=15)
    assert result["status"] == "failed"


def test_process_limit(runtime):  # type: ignore[no-untyped-def]
    result = run(
        runtime,
        """import os,time,signal,json
from pathlib import Path
children=[];limited=False
try:
 for i in range(100):
  try:
   pid=os.fork()
  except OSError:limited=True;break
  if pid==0:time.sleep(5);os._exit(0)
  children.append(pid)
finally:
 for pid in children:
  os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
Path('pids.json').write_text(json.dumps({'limited':limited,'count':len(children)}))""",
    )
    assert result["status"] == "completed", result
    data = json.loads(result["files"]["pids.json"])
    assert data["limited"] and data["count"] < 64


def test_excessive_output(runtime):  # type: ignore[no-untyped-def]
    result = run(
        runtime,
        "from pathlib import Path\nf=Path('large.txt').open('wb')\nwhile True:f.write(b'x'*1024**2)",
        seconds=10,
    )
    assert result["status"] in {"failed", "timed_out"}
    assert sum(map(len, result["files"].values())) <= 128 * 1024**2


def test_spice(runtime):  # type: ignore[no-untyped-def]
    deck = b"RC\nV1 a 0 1\nR1 a b 1k\nC1 b 0 1u\n.control\ntran .0001 .01\nwrdata /out/trace.txt v(b)\nquit\n.endc\n.end\n"
    result = run(runtime, "", kind="spice", inputs={"circuit.cir": deck})
    assert result["status"] == "completed" and len(result["files"]["trace.txt"]) > 50


def test_trusted_rehearsal_and_repeatability(runtime, value):  # type: ignore[no-untyped-def]
    data = {**value, "seed": 11}
    first = run(runtime, "", seconds=60, kind="rehearsal", inputs={"snapshot.json": encoded(data)})
    second = run(runtime, "", seconds=60, kind="rehearsal", inputs={"snapshot.json": encoded(data)})
    assert first["status"] == second["status"] == "completed"
    assert verify_rehearsal(data, first["files"])["passed"]
    assert verify_rehearsal(data, second["files"])["passed"]
    import csv
    import io

    a = list(csv.DictReader(io.StringIO(first["files"]["candidate_procedure.csv"].decode())))
    b = list(csv.DictReader(io.StringIO(second["files"]["candidate_procedure.csv"].decode())))
    assert len(a) >= 10 and len(b) >= 10
    for x, y in zip(a[:10], b[:10], strict=True):
        assert abs(float(x["jacket_c_value"]) - float(y["jacket_c_value"])) <= 0.00005
