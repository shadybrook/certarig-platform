#!/usr/bin/env bash
# Install or upgrade the CertaRig Edge node on a Raspberry Pi (Debian/Raspberry Pi OS).
#
#   sudo deploy/install_pi.sh [--source DIR] [--operator-key KEY] [--agent-key KEY] [--no-start]
#
# What it does, idempotently:
#   1. creates the `certarig` service user (groups gpio, i2c) and /etc/certarig, /var/lib/certarig
#   2. copies the repository into /opt/certarig and builds a venv with the `pi` extra
#   3. writes /etc/certarig/edge.env with operator/agent keys (generated if not given; never printed twice)
#   4. installs config/rig.wave1.json + capabilities.wave1.json as /etc/certarig/{rig,capabilities}.json
#      unless those files already exist
#   5. installs the systemd unit and the narrow sudoers rule for `systemctl poweroff`
#   6. enables and starts the service, then prints /health
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPERATOR_KEY=""
AGENT_KEY=""
START=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --operator-key) OPERATOR_KEY="$2"; shift 2 ;;
    --agent-key) AGENT_KEY="$2"; shift 2 ;;
    --no-start) START=0; shift ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "run as root: sudo $0 $*" >&2
  exit 1
fi

PREFIX=/opt/certarig
ETC=/etc/certarig
VAR=/var/lib/certarig

echo "[1/6] service user and directories"
id -u certarig >/dev/null 2>&1 || useradd --system --home-dir "$VAR" --shell /usr/sbin/nologin certarig
for grp in gpio i2c spi; do getent group "$grp" >/dev/null && usermod -aG "$grp" certarig || true; done
install -d -m 0750 -o certarig -g certarig "$VAR" "$VAR/evidence"
install -d -m 0750 -o root -g certarig "$ETC"

echo "[2/6] code and virtualenv in $PREFIX"
install -d -m 0755 "$PREFIX"
rsync -a --delete --exclude '.git' --exclude '.venv' --exclude 'evidence' --exclude '__pycache__' \
  --exclude 'node_modules' "$SOURCE/" "$PREFIX/"
if [[ ! -x "$PREFIX/.venv/bin/python" ]]; then
  python3 -m venv "$PREFIX/.venv"
fi
"$PREFIX/.venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/.venv/bin/pip" install --quiet -e "$PREFIX[pi]"
chown -R certarig:certarig "$PREFIX"

echo "[3/6] keys in $ETC/edge.env"
if [[ ! -f "$ETC/edge.env" ]]; then
  OPERATOR_KEY="${OPERATOR_KEY:-$(openssl rand -hex 24)}"
  AGENT_KEY="${AGENT_KEY:-$(openssl rand -hex 24)}"
  umask 077
  cat > "$ETC/edge.env" <<ENV
# Written by deploy/install_pi.sh on $(date -Is). Rotate by editing and restarting certarig-edge.
CERTARIG_OPERATOR_KEY=$OPERATOR_KEY
CERTARIG_AGENT_KEY=$AGENT_KEY
# Set to 1 only after the bench has been inspected. 0 keeps GPIO23 low whatever the kernel decides.
CERTARIG_ENABLE_ACTUATION=0
# What /v1/ops/shutdown runs after forcing safe and flushing evidence.
CERTARIG_POWEROFF_CMD=sudo -n systemctl poweroff
ENV
  umask 022
  chown root:certarig "$ETC/edge.env"; chmod 0640 "$ETC/edge.env"
  echo "    operator key: $OPERATOR_KEY"
  echo "    agent key:    $AGENT_KEY"
  echo "    (shown once; they are in $ETC/edge.env)"
else
  echo "    keeping existing $ETC/edge.env"
fi

echo "[4/6] rig and capability documents"
[[ -f "$ETC/rig.json" ]] || install -m 0640 -o root -g certarig "$SOURCE/config/rig.wave1.json" "$ETC/rig.json"
[[ -f "$ETC/capabilities.json" ]] || install -m 0640 -o root -g certarig "$SOURCE/config/capabilities.wave1.json" "$ETC/capabilities.json"

echo "[5/6] systemd unit and sudoers rule"
install -m 0644 "$SOURCE/deploy/certarig-edge.service" /etc/systemd/system/certarig-edge.service
install -m 0440 "$SOURCE/deploy/certarig-sudoers" /etc/sudoers.d/certarig
visudo -cf /etc/sudoers.d/certarig >/dev/null
systemctl daemon-reload
systemctl enable certarig-edge.service >/dev/null

if [[ $START -eq 1 ]]; then
  echo "[6/6] starting"
  systemctl restart certarig-edge.service
  for _ in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then break; fi
    sleep 0.5
  done
  curl -fsS http://127.0.0.1:8080/health || { journalctl -u certarig-edge -n 40 --no-pager; exit 1; }
  echo
  echo "Studio: http://$(hostname).local:8080/"
else
  echo "[6/6] not started (--no-start)"
fi
