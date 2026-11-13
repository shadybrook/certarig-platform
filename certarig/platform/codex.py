"""Local Codex 0.146.1 stdio provider. No inherited tools or API-key fallback."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from certarig.agent.providers.base import Message, ProviderError, ProviderResponse, ToolCall, ToolSpec

VERSION = "0.146.1"
DISABLED = (
    "shell_tool",
    "unified_exec",
    "apps",
    "multi_agent",
    "multi_agent_v2",
    "plugins",
    "remote_plugin",
    "hooks",
    "memories",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "in_app_browser",
    "image_generation",
    "code_mode",
    "code_mode_host",
    "skill_search",
    "skill_mcp_dependency_install",
    "workspace_dependencies",
    "request_permissions_tool",
    "tool_suggest",
)


class RPC:
    def __init__(self, profile: Path):
        executable = shutil.which("codex")
        if (
            not executable
            or subprocess.run([executable, "--version"], capture_output=True, timeout=5, check=False)
            .stdout.decode()
            .strip()
            != "codex-cli " + VERSION
        ):
            raise ProviderError("Codex CLI " + VERSION + " is required; requalify other versions")
        profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        if profile.is_symlink() or profile.stat().st_mode & 0o077:
            raise ProviderError("Codex requires a dedicated private profile")
        cwd = profile / "empty-workspace"
        cwd.mkdir(exist_ok=True, mode=0o700)
        # Only minimal OS transport environment. No API keys, proxy credentials or inherited MCP config.
        env = {
            k: v
            for k, v in os.environ.items()
            if k in {"PATH", "HOME", "TMPDIR", "LANG", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        }
        env["CODEX_HOME"] = str(profile.resolve())
        args = [
            executable,
            "-c",
            'cli_auth_credentials_store="file"',
            "-c",
            'web_search="disabled"',
            "-c",
            "mcp_servers={}",
            "-c",
            "project_doc_max_bytes=0",
        ]
        for feature in DISABLED:
            args.extend(["-c", "features." + feature + "=false"])
        args.extend(["app-server", "--listen", "stdio://"])
        self.process = subprocess.Popen(
            args, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self.inbox: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=256)
        self.write_lock = threading.Lock()
        self.counter, self.cwd = 0, str(cwd.resolve())
        self.deferred: list[dict[str, Any]] = []
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.request(
            "initialize",
            {
                "clientInfo": {"name": "certarig", "version": "0.5.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        self.send({"method": "initialized", "params": {}})

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            while line := self.process.stdout.readline(1024 * 1024 + 1):
                if len(line) > 1024 * 1024:
                    break
                value = json.loads(line)
                self.inbox.put(value, timeout=1)
        except (ValueError, queue.Full):
            pass
        try:
            self.inbox.put({"error": {"message": "Codex transport closed"}}, timeout=1)
        except queue.Full:
            pass

    def send(self, value: dict[str, Any]) -> None:
        with self.write_lock:
            try:
                assert self.process.stdin is not None
                self.process.stdin.write(json.dumps(value).encode() + b"\n")
                self.process.stdin.flush()
            except (OSError, ValueError) as exc:
                raise ProviderError("Codex transport disconnected") from exc

    def next(self, timeout: float = 120) -> dict[str, Any]:
        if getattr(self, "deferred", []):
            return self.deferred.pop(0)
        try:
            value = self.inbox.get(timeout=timeout)
        except queue.Empty as exc:
            if timeout <= 1:
                return {}
            raise ProviderError("Codex response deadline exceeded") from exc
        if value.get("error"):
            raise ProviderError(str(value["error"].get("message", "Codex request failed"))[:500])
        return value

    def deny(self, message: dict[str, Any]) -> None:
        self.send(
            {
                "id": message["id"],
                "error": {
                    "code": -32601,
                    "message": "CertaRig denies native tools, file access, permissions and external requests",
                },
            }
        )

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.counter += 1
        identifier = self.counter
        self.send({"id": identifier, "method": method, "params": params})
        deadline = time.monotonic() + 30
        deferred: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            message = self.next(max(0.01, deadline - time.monotonic()))
            if message.get("id") == identifier and "result" in message:
                self.deferred = deferred + getattr(self, "deferred", [])
                return dict(message["result"])
            deferred.append(message)
            if len(deferred) > 256:
                raise ProviderError("Codex notification quota exceeded")
        raise ProviderError("Codex request deadline exceeded")

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()


class CodexProvider:
    name = "codex-local"

    def __init__(self, profile: Path, model: str, rpc: Any = None):
        self.rpc, self.model = rpc or RPC(profile), model
        self.thread: str | None = None
        self.turn: str | None = None
        self.pending: dict[str, Any] | None = None
        self.cancelled = threading.Event()
        self.usage: dict[str, int] = {}
        self.reported_model = model

    def account(self) -> dict[str, Any]:
        raw = self.rpc.request("account/read", {"refreshToken": True})
        account = raw.get("account") or {}
        # Never return tokens or identity email to another application user.
        return {
            "connected": account.get("type") == "chatgpt",
            "type": account.get("type"),
            "requires_auth": raw.get("requiresOpenaiAuth", True),
        }

    def login(self) -> dict[str, Any]:
        raw = self.rpc.request("account/login/start", {"type": "chatgptDeviceCode"})
        return {k: raw[k] for k in ("type", "loginId", "verificationUrl", "userCode") if k in raw}

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        if self.cancelled.is_set():
            raise ProviderError("Inference revoked")
        if self.thread is None:
            if not self.account()["connected"]:
                raise ProviderError("Connect a dedicated ChatGPT account; no paid API fallback")
            models = self.rpc.request("model/list", {"includeHidden": False})
            if not any(row.get("model") == self.model for row in models.get("data", [])):
                raise ProviderError("Requested model is not available to this connection")
            value = self.rpc.request(
                "thread/start",
                {
                    "model": self.model,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "cwd": self.rpc.cwd,
                    "baseInstructions": system,
                    "ephemeral": True,
                    "environments": [],
                    "selectedCapabilityRoots": [],
                    "dynamicTools": [
                        {
                            "type": "function",
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.parameters,
                        }
                        for t in tools
                    ],
                },
            )
            self.thread = value["thread"]["id"]
            self.reported_model = value.get("model", self.model)
            if self.reported_model != self.model:
                raise ProviderError("Codex substituted a different model; re-evaluation required")
        if self.pending:
            result = next(
                (
                    m
                    for m in reversed(messages)
                    if m.role == "tool" and m.tool_call_id == self.pending["params"]["callId"]
                ),
                None,
            )
            if result is None:
                raise ProviderError("Missing scoped dynamic tool result")
            self.rpc.send(
                {
                    "id": self.pending["id"],
                    "result": {
                        "contentItems": [{"type": "inputText", "text": result.content}],
                        "success": "scope_denied" not in result.content,
                    },
                }
            )
            self.pending = None
        else:
            response = self.rpc.request(
                "turn/start",
                {
                    "threadId": self.thread,
                    "input": [{"type": "text", "text": messages[-1].content}],
                    "environments": [],
                },
            )
            self.turn = response["turn"]["id"]
        text = []
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and not self.cancelled.is_set():
            event = self.rpc.next(min(1, max(0.01, deadline - time.monotonic())))
            method, params = event.get("method", ""), event.get("params", {})
            if method == "item/tool/call" and "id" in event:
                if params.get("threadId") != self.thread or params.get("turnId") != self.turn:
                    self.rpc.deny(event)
                    raise ProviderError("Dynamic tool belongs to another turn")
                self.pending = event
                return ProviderResponse(
                    None,
                    [ToolCall(params["callId"], params["tool"], params["arguments"])],
                    model=self.reported_model,
                )
            if "id" in event and "method" in event:
                self.rpc.deny(event)
                raise ProviderError("Unapproved native capability requested")
            if method == "item/started" and params.get("item", {}).get("type") not in {
                "agentMessage",
                "reasoning",
                "dynamicToolCall",
                "userMessage",
            }:
                self.cancel()
                raise ProviderError("Unexpected native tool; Codex boundary requires requalification")
            if method == "item/agentMessage/delta":
                text.append(params.get("delta", ""))
                if sum(map(len, text)) > 32000:
                    self.cancel()
                    raise ProviderError("Model output quota exceeded")
            if method == "thread/tokenUsage/updated":
                self.usage = {
                    k: v
                    for k, v in params.get("tokenUsage", {}).get("last", {}).items()
                    if isinstance(v, int)
                }
            if method == "turn/completed":
                if params["turn"]["status"] != "completed":
                    raise ProviderError("Codex turn failed or quota exhausted; no provider fallback")
                self.turn = None
                return ProviderResponse("".join(text), usage=self.usage, model=self.reported_model)
        self.cancel()
        raise ProviderError("Inference cancelled or timed out")

    def cancel(self) -> None:
        self.cancelled.set()
        if self.thread and self.turn:
            self.rpc.send(
                {
                    "id": "cancel",
                    "method": "turn/interrupt",
                    "params": {"threadId": self.thread, "turnId": self.turn},
                }
            )

    def close(self) -> None:
        self.cancel()
        self.rpc.close()
