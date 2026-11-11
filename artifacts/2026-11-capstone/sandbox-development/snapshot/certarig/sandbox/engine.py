"""Fixed Docker launch policy. This module never runs submitted content on the host."""

from __future__ import annotations

import base64
import io
import json
import platform
import re
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from threading import Event, Thread, Timer
from typing import Any

from .contracts import CONTEXT, LIMITS, PROFILE, safe_name


def command(args: list[str], timeout: float = 10) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, capture_output=True, timeout=timeout, check=False)


def resource_preflight(path: Path) -> dict[str, Any]:
    free = shutil.disk_usage(path).free
    reasons = []
    if free < LIMITS["disk_free_bytes"]:
        reasons.append("At least 8 GiB free disk space is required; no existing files will be deleted")
    pressure: int | None = None
    if platform.system() == "Darwin":
        try:
            pressure = int(command(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            reasons.append("Cannot establish macOS memory pressure")
        if pressure not in {None, 1}:
            reasons.append("macOS memory pressure is elevated; close workloads manually")
    elif platform.system() != "Linux":
        reasons.append("Only macOS Colima and Linux qualification are supported")
    return {"ready": not reasons, "free_bytes": free, "memory_pressure": pressure, "blockers": reasons}


def collect_archive(data: bytes) -> dict[str, bytes]:
    """Docker archives are attacker-controlled. Never extract them into host paths."""
    if len(data) > LIMITS["output_bytes"] + 2 * 1024**2:
        raise ValueError("output archive too large")
    result: dict[str, bytes] = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            if member.isdir() and member.name == "out":
                continue
            name = member.name.removeprefix("out/")
            if not safe_name(name) or not member.isfile() or member.name == name:
                raise ValueError("unsafe artifact path/type")
            if Path(name).suffix.lower() not in {
                ".json",
                ".csv",
                ".txt",
                ".log",
                ".png",
                ".gz",
                ".cir",
                ".py",
            }:
                raise ValueError("unsupported artifact type")
            total += member.size
            if total > LIMITS["output_bytes"] or len(result) >= 512 or name in result:
                raise ValueError("artifact quota or duplicate name")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("artifact is not a regular file")
            result[name] = stream.read(member.size + 1)
            if len(result[name]) != member.size:
                raise ValueError("incomplete artifact")
    return result


class DockerEngine:
    def __init__(self, image: str, root: Path, *, qualification_mode: bool = False) -> None:
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise ValueError("sandbox image must be an immutable image ID")
        self.image, self.root = image, root
        self.qualification_mode = qualification_mode

    @property
    def current_image(self) -> str:
        return (self.root / "image.id").read_text().strip()

    def docker(self, *args: str, timeout: float = 10) -> subprocess.CompletedProcess[bytes]:
        return command(["docker", "--context", CONTEXT, *args], timeout)

    def preflight(self) -> dict[str, Any]:
        result = resource_preflight(self.root)
        try:
            if self.current_image != self.image:
                result["blockers"].append("Image lock changed; restart and requalify the broker")
            context = command(["docker", "context", "inspect", CONTEXT])
            endpoint = json.loads(context.stdout)[0]["Endpoints"]["docker"]["Host"]
            expected = "unix://" + str(Path.home() / ".colima" / PROFILE / "docker.sock")
            if endpoint != expected:
                result["blockers"].append("Sandbox context must use the dedicated Colima socket")
            mounts = command(
                ["colima", "ssh", PROFILE, "--", "findmnt", "-rn", "-t", "virtiofs,9p,fuse.sshfs"]
            )
            if mounts.returncode != 1 or mounts.stdout.strip():
                result["blockers"].append("VM host shares must be disabled and verified")
            info = json.loads(self.docker("info", "--format", "{{json .}}").stdout)
            if (
                not any("seccomp" in s for s in info.get("SecurityOptions", []))
                or info.get("MemoryLimit") is not True
                or info.get("PidsLimit") is not True
                or info.get("SwapLimit") is not True
            ):
                result["blockers"].append("Required kernel resource/seccomp enforcement unavailable")
            image = json.loads(self.docker("image", "inspect", self.image).stdout)[0]
            if (
                image["Architecture"] != "arm64"
                or image["Os"] != "linux"
                or image["Config"]["Labels"].get("org.certarig.sandbox") != "v1"
            ):
                result["blockers"].append("Unqualified sandbox image/platform")
        except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired):
            result["blockers"].append("Dedicated runtime or pinned image unavailable")
        qualification = self.root / "qualification.json"
        qualified = False
        try:
            record = json.loads(qualification.read_text())
            qualified = (
                record.get("image") == self.image
                and record.get("passed") is True
                and record.get("suite") == "sandbox-runtime-v1"
            )
        except (OSError, ValueError):
            pass
        if not qualified and not self.qualification_mode:
            result["blockers"].append(
                "Pinned image has not passed the real-container isolation/fault qualification"
            )
        result["qualified"] = qualified
        result["ready"] = not result["blockers"]
        return result

    def create_args(self, name: str, kind: str, seconds: int) -> list[str]:
        return [
            "create",
            "--interactive",
            "--name",
            name,
            "--label",
            "org.certarig.sandbox=v1",
            "--label",
            f"org.certarig.root={self.root.resolve()}",
            "--network",
            "none",
            "--user",
            "10001:10001",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "1",
            "--memory",
            "512m",
            "--memory-swap",
            "512m",
            "--pids-limit",
            "64",
            "--cgroupns",
            "private",
            "--ulimit",
            "nofile=128:128",
            "--ulimit",
            "fsize=134217728:134217728",
            "--log-driver",
            "local",
            "--log-opt",
            "max-size=1m",
            "--log-opt",
            "max-file=1",
            "--tmpfs",
            "/out:rw,noexec,nosuid,nodev,size=134217728,nr_inodes=1024,uid=10001,gid=10001",
            "--tmpfs",
            "/scratch:rw,noexec,nosuid,nodev,size=268435456,nr_inodes=2048,uid=10001,gid=10001",
            "--env",
            "MPLCONFIGDIR=/scratch/matplotlib",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            self.image,
            "timeout",
            "--signal=KILL",
            f"{seconds}s",
            "python",
            "-m",
            "certarig.sandbox.worker",
            kind,
            str(seconds),
        ]

    def cleanup(self, name: str) -> None:
        if not re.fullmatch(r"crsb-job_[a-f0-9]{16}", name):
            raise ValueError("not a sandbox container name")
        inspected = self.docker("inspect", name)
        if inspected.returncode:
            return
        labels = json.loads(inspected.stdout)[0]["Config"].get("Labels") or {}
        if labels.get("org.certarig.sandbox") != "v1" or labels.get("org.certarig.root") != str(
            self.root.resolve()
        ):
            raise ValueError("refusing to remove an unrelated container")
        self.docker("rm", "-f", name)

    def run(
        self, job_id: str, kind: str, inputs: dict[str, bytes], seconds: int, cancel: Event
    ) -> dict[str, Any]:
        check = self.preflight()
        if not check["ready"]:
            raise RuntimeError("; ".join(check["blockers"]))
        name = "crsb-" + job_id
        if sum(map(len, inputs.values())) > LIMITS["input_bytes"]:
            raise ValueError("input quota exceeded")
        if any(not safe_name(k) for k in inputs):
            raise ValueError("unsafe input name")
        payload = json.dumps({k: base64.b64encode(v).decode() for k, v in inputs.items()}).encode()
        began = time.monotonic()
        writer: subprocess.Popen[bytes] | None = None
        watchdog: Timer | None = None
        deadline = Event()
        try:
            created = self.docker(*self.create_args(name, kind, seconds))
            if created.returncode:
                raise RuntimeError(created.stderr[:2000].decode(errors="replace"))

            def expire() -> None:
                deadline.set()
                self.docker("kill", name, timeout=3)

            watchdog = Timer(max(0.001, seconds - (time.monotonic() - began)), expire)
            watchdog.daemon = True
            watchdog.start()
            # Stream data over stdin: neither rootfs writes nor host mounts are needed.
            writer = subprocess.Popen(
                ["docker", "--context", CONTEXT, "start", "-i", name],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            def send() -> None:
                try:
                    assert writer is not None and writer.stdin is not None
                    writer.stdin.write(payload)
                    writer.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            Thread(target=send, daemon=True).start()
            reason = "failed"
            files: dict[str, bytes] = {}
            state: dict[str, Any] = {}
            while True:
                state = json.loads(self.docker("inspect", "--format", "{{json .State}}", name).stdout)
                if not state["Running"]:
                    reason = (
                        "timed_out" if deadline.is_set() else "cancelled" if cancel.is_set() else "failed"
                    )
                    break
                if cancel.is_set():
                    reason = "cancelled"
                    break
                if time.monotonic() - began >= seconds:
                    reason = "timed_out"
                    break
                if self.docker("exec", name, "test", "-f", "/scratch/worker.done").returncode == 0:
                    # tmpfs vanishes after exit. Freeze the live container before collecting.
                    if self.docker("pause", name).returncode:
                        raise RuntimeError("Cannot freeze output collection")
                    archive = self.docker("cp", name + ":/out", "-", timeout=15)
                    if archive.returncode:
                        raise RuntimeError("Cannot collect sandbox output")
                    files = collect_archive(archive.stdout)
                    meta = json.loads(files.get("worker_record.json", b"{}"))
                    reason = "completed" if meta.get("exit_code") == 0 else "failed"
                    break
                cancel.wait(0.1)
            files["worker.log"] = self.docker("logs", "--tail", "1000", name).stdout[-(1024**2) :]
            return {
                "status": reason,
                "files": files,
                "resource": {
                    "elapsed_s": time.monotonic() - began,
                    "exit_code": state.get("ExitCode"),
                    "oom_killed": state.get("OOMKilled"),
                    "limits": LIMITS,
                },
            }
        finally:
            if watchdog is not None:
                watchdog.cancel()
            self.cleanup(name)
            if writer is not None:
                try:
                    writer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    writer.kill()
                    writer.wait(timeout=5)
