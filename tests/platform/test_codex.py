"""Pinned app-server protocol doubles. They do not establish live-provider qualification."""

import io
import json
import queue
from pathlib import Path
from types import SimpleNamespace

import pytest

from certarig.agent.providers.base import Message, ProviderError, ToolSpec
from certarig.platform.codex import DISABLED, RPC, CodexProvider


class Wire:
    cwd = "/private/empty"

    def __init__(self, events=None):
        self.events = list(events or [])
        self.sent = []
        self.closed = False
        self.connected = True
        self.model = "test-model"

    def request(self, method, params):
        self.sent.append({"method": method, "params": params})
        return {
            "account/read": {"account": {"type": "chatgpt" if self.connected else None}},
            "model/list": {"data": [{"model": self.model}]},
            "thread/start": {"thread": {"id": "thread"}, "model": self.model},
            "turn/start": {"turn": {"id": "turn"}},
        }[method]

    def send(self, value):
        self.sent.append(value)

    def next(self, timeout=120):
        return self.events.pop(0)

    def deny(self, value):
        self.sent.append({"denied": value})

    def close(self):
        self.closed = True


def done(status="completed"):
    return {"method": "turn/completed", "params": {"turn": {"status": status}}}


def provider(events):
    wire = Wire(events)
    return CodexProvider(Path("/unused"), "test-model", wire), wire


def test_dynamic_tools_use_existing_session_protocol_and_scoped_results():
    tool = {
        "id": 500,
        "method": "item/tool/call",
        "params": {
            "threadId": "thread",
            "turnId": "turn",
            "callId": "call",
            "tool": "read_signals",
            "arguments": {},
        },
    }
    p, wire = provider(
        [
            tool,
            {
                "method": "item/agentMessage/delta",
                "params": {"delta": '{"status":"ready","reason":"observed"}'},
            },
            {
                "method": "thread/tokenUsage/updated",
                "params": {"tokenUsage": {"last": {"inputTokens": 10, "outputTokens": 5}}},
            },
            done(),
        ]
    )
    specs = [ToolSpec("read_signals", "Read this bench", {"type": "object"})]
    result = p.complete("system", [Message("user", "assess")], specs)
    assert result.tool_calls[0].name == "read_signals"
    thread = next(m for m in wire.sent if m.get("method") == "thread/start")["params"]
    assert thread["environments"] == [] and thread["sandbox"] == "read-only"
    assert thread["dynamicTools"][0]["type"] == "function"
    result = p.complete(
        "system", [Message("user", "assess"), Message("tool", '{"value":25}', tool_call_id="call")], specs
    )
    assert json.loads(result.text)["status"] == "ready" and result.model == "test-model"
    assert result.usage["inputTokens"] == 10
    assert any(
        m.get("id") == 500 and m["result"]["contentItems"][0]["text"] == '{"value":25}' for m in wire.sent
    )
    p.close()
    assert wire.closed


@pytest.mark.parametrize(
    "event",
    [
        {
            "id": 1,
            "method": "item/tool/call",
            "params": {
                "threadId": "other",
                "turnId": "turn",
                "callId": "call",
                "tool": "read_signals",
                "arguments": {},
            },
        },
        {"id": 1, "method": "item/fileChange/requestApproval", "params": {}},
        {"method": "item/started", "params": {"item": {"type": "commandExecution"}}},
        done("failed"),
    ],
)
def test_native_file_command_cross_thread_and_failed_turn_refuse(event):
    p, wire = provider([event])
    with pytest.raises(ProviderError):
        p.complete("system", [Message("user", "assess")], [])
    p.close()
    assert wire.closed


def test_disconnected_missing_model_cancellation_and_missing_result():
    p, wire = provider([])
    wire.connected = False
    with pytest.raises(ProviderError, match="Connect"):
        p.complete("", [Message("user", "x")], [])
    p.close()
    p, wire = provider([])
    wire.model = "unavailable"
    with pytest.raises(ProviderError, match="not available"):
        p.complete("", [Message("user", "x")], [])
    p.close()
    p, wire = provider([])
    p.cancel()
    with pytest.raises(ProviderError, match="revoked"):
        p.complete("", [], [])
    p.close()
    p, wire = provider([])
    p.thread = "thread"
    p.pending = {"id": 1, "params": {"callId": "missing"}}
    with pytest.raises(ProviderError, match="Missing"):
        p.complete("", [], [])
    p.close()


def test_login_account_only_exposes_managed_signin_fields():
    p, wire = provider([])
    assert p.account()["connected"]

    def request(method, params):
        assert method == "account/login/start" and params == {"type": "chatgptDeviceCode"}
        return {
            "type": "chatgptDeviceCode",
            "verificationUrl": "https://auth.openai.com/codex/device",
            "userCode": "test-code",
            "loginId": "login",
            "secret": "never-return",
        }

    wire.request = request
    assert "secret" not in p.login()
    p.close()


class Process:
    def __init__(self):
        self.stdout = io.BytesIO(b'{"id":1,"result":{}}\n')
        self.stdin = io.BytesIO()
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True

    def wait(self, timeout):
        return 0


def test_rpc_launch_is_fixed_private_and_has_no_inherited_api_or_tools(tmp_path, monkeypatch):
    captured = {}
    proc = Process()
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("PRIVATE_CREDENTIAL", "must-not-inherit")
    monkeypatch.setattr("certarig.platform.codex.shutil.which", lambda command: "/usr/bin/codex")
    monkeypatch.setattr(
        "certarig.platform.codex.subprocess.run",
        lambda *a, **kw: SimpleNamespace(stdout=b"codex-cli 0.146.1\n"),
    )

    def spawn(args, **kw):
        captured.update(args=args, **kw)
        return proc

    monkeypatch.setattr("certarig.platform.codex.subprocess.Popen", spawn)
    rpc = RPC(tmp_path / "private")
    assert "OPENAI_API_KEY" not in captured["env"] and "PRIVATE_CREDENTIAL" not in captured["env"]
    assert captured["env"]["CODEX_HOME"] == str(tmp_path / "private")
    for name in DISABLED:
        assert "features." + name + "=false" in captured["args"]
    assert "mcp_servers={}" in captured["args"]
    assert json.loads(proc.stdin.getvalue().splitlines()[0])["method"] == "initialize"
    rpc.close()
    assert proc.terminated


def test_rpc_version_private_mode_error_frames_and_deadlines(tmp_path, monkeypatch):
    monkeypatch.setattr("certarig.platform.codex.shutil.which", lambda command: None)
    with pytest.raises(ProviderError, match="required"):
        RPC(tmp_path / "private")
    monkeypatch.setattr("certarig.platform.codex.shutil.which", lambda command: "/usr/bin/codex")
    monkeypatch.setattr(
        "certarig.platform.codex.subprocess.run",
        lambda *a, **kw: SimpleNamespace(stdout=b"codex-cli 0.146.1\n"),
    )
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(ProviderError, match="private"):
        RPC(public)
    rpc = RPC.__new__(RPC)
    rpc.inbox = queue.Queue()
    rpc.counter = 0
    rpc.inbox.put({"error": {"message": "quota exhausted"}})
    with pytest.raises(ProviderError, match="quota"):
        rpc.next()
    assert rpc.next(0.001) == {}
    with pytest.raises(ProviderError, match="deadline"):
        rpc.next(1.001)
    rpc.process = SimpleNamespace(stdin=io.BytesIO())
    rpc.write_lock = __import__("threading").Lock()
    rpc.deny({"id": 99})
    assert json.loads(rpc.process.stdin.getvalue())["error"]["code"] == -32601
    rpc.process.stdin.close()
    with pytest.raises(ProviderError, match="disconnected"):
        rpc.send({})
