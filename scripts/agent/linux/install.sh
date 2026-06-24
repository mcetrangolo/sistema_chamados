#!/bin/sh
set -eu

DEFAULT_SERVER_URL="__SERVER_URL_DEFAULT__"
AGENT_TOKEN="__AGENT_TOKEN_DEFAULT__"
INSTALL_DIR="/opt/sistema-chamados-agent"
CONFIG_DIR="/etc/sistema-chamados-agent"
CONFIG_FILE="$CONFIG_DIR/config.env"
LOG_FILE="/var/log/sistema-chamados-agent.log"

need_root() {
  if [ "$(id -u)" != "0" ]; then
    echo "Execute como root: sudo sh install.sh"
    exit 1
  fi
}

ask() {
  prompt="$1"
  default="$2"
  printf "%s [%s]: " "$prompt" "$default"
  read -r value || value=""
  if [ -z "$value" ]; then
    value="$default"
  fi
  printf "%s" "$value"
}

normalize_url() {
  value="$1"
  case "$value" in
    http://*|https://*) ;;
    *) value="http://$value" ;;
  esac
  printf "%s" "$value" | sed 's:/*$::'
}

need_root

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 nao encontrado. Instale python3 antes de continuar."
  exit 1
fi

echo "Instalador do Agente Linux do Sistema de Chamados"
case "$DEFAULT_SERVER_URL" in
  __*__) DEFAULT_SERVER_URL="http://" ;;
esac
case "$AGENT_TOKEN" in
  __*__) AGENT_TOKEN="$(ask "Token do agente" "")" ;;
esac
if [ -z "$AGENT_TOKEN" ]; then
  echo "O token do agente e obrigatorio. Consulte Inventario > Agentes de inventario."
  exit 1
fi
server_url="$(ask "Informe o IP:porta ou URL do servidor" "$DEFAULT_SERVER_URL")"
server_url="$(normalize_url "$server_url")"
serial_manual="$(ask "Numero de serie manual/patrimonio opcional" "")"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"

cat > "$INSTALL_DIR/agent.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import platform
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def read_config(path):
    config = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"')
    return config


def run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=8).strip()
    except Exception:
        return ""


def read_first(paths):
    for path in paths:
        try:
            value = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
            if value:
                return value
        except Exception:
            pass
    return ""


def os_release():
    data = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value.strip().strip('"')
    except Exception:
        pass
    return data


def primary_ipv4():
    route = run(["sh", "-c", "ip route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if ($i==\"src\") print $(i+1)}' | head -n1"])
    if route:
        return route
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def interfaces():
    items = []
    base = Path("/sys/class/net")
    if not base.exists():
        return items
    for item in sorted(base.iterdir()):
        name = item.name
        if name == "lo":
            continue
        mac = read_first([item / "address"])
        state = read_first([item / "operstate"])
        ip = run(["sh", "-c", "ip -4 addr show dev %s | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1" % name])
        items.append({"nome": name, "ip": ip, "mac": mac, "status": state, "velocidade": read_first([item / "speed"])})
    return items


def installed_software():
    if run(["sh", "-c", "command -v dpkg-query"]):
        output = run(["sh", "-c", "dpkg-query -W -f='${Package} ${Version}\\n' | head -n 200"])
        return [line for line in output.splitlines() if line.strip()]
    if run(["sh", "-c", "command -v rpm"]):
        output = run(["sh", "-c", "rpm -qa | sort | head -n 200"])
        return [line for line in output.splitlines() if line.strip()]
    return []


def disk_total_gb():
    output = run(["sh", "-c", "df -B1 --total -x tmpfs -x devtmpfs 2>/dev/null | awk '/total/ {print $2}'"])
    try:
        return round(int(output) / (1024 ** 3), 2)
    except Exception:
        return None


def memory_total_gb():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / 1024 / 1024, 2)
    except Exception:
        pass
    return None


def payload(config):
    osr = os_release()
    ifaces = interfaces()
    ip = primary_ipv4()
    primary = next((i for i in ifaces if i.get("ip") == ip), ifaces[0] if ifaces else {})
    serial = config.get("SERIAL_MANUAL") or read_first([
        "/sys/class/dmi/id/product_serial",
        "/sys/class/dmi/id/board_serial",
        "/sys/class/dmi/id/chassis_serial",
    ])
    cpu = run(["sh", "-c", "awk -F: '/model name/ {print $2; exit}' /proc/cpuinfo | sed 's/^ //'"])
    office = run(["sh", "-c", "command -v libreoffice >/dev/null 2>&1 && libreoffice --version | head -n1 || true"])
    return {
        "versao_agente": "1.3.0",
        "hostname": socket.gethostname(),
        "ip": ip,
        "mac": primary.get("mac", ""),
        "usuario_logado": run(["sh", "-c", "who | awk '{print $1}' | head -n1"]) or os.environ.get("USER", ""),
        "dominio": run(["sh", "-c", "dnsdomainname 2>/dev/null || hostname -d 2>/dev/null || true"]),
        "fabricante": read_first(["/sys/class/dmi/id/sys_vendor"]),
        "modelo": read_first(["/sys/class/dmi/id/product_name"]),
        "numero_serie": serial,
        "sistema_operacional": (osr.get("PRETTY_NAME") or platform.platform()),
        "arquitetura": platform.machine(),
        "processador": cpu,
        "memoria_total_gb": memory_total_gb(),
        "disco_total_gb": disk_total_gb(),
        "office": office,
        "softwares_instalados": installed_software(),
        "interfaces": ifaces,
    }


def send(config, data):
    server = config["SERVER_URL"].rstrip("/")
    endpoint = server + "/inventario/agente/coleta/"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + config["TOKEN"])
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/sistema-chamados-agent/config.env"
    config = read_config(config_path)
    result = send(config, payload(config))
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERRO: %s" % exc, file=sys.stderr)
        sys.exit(1)
PY

chmod 0755 "$INSTALL_DIR/agent.py"

cat > "$CONFIG_FILE" <<EOF
SERVER_URL="$server_url"
TOKEN="$AGENT_TOKEN"
SERIAL_MANUAL="$serial_manual"
EOF
chmod 0600 "$CONFIG_FILE"

if command -v systemctl >/dev/null 2>&1; then
  cat > /etc/systemd/system/sistema-chamados-agent.service <<EOF
[Unit]
Description=Sistema Chamados Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py $CONFIG_FILE
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
EOF

  cat > /etc/systemd/system/sistema-chamados-agent.timer <<EOF
[Unit]
Description=Executa Sistema Chamados Agent periodicamente

[Timer]
OnBootSec=2min
OnUnitActiveSec=6h
Unit=sistema-chamados-agent.service

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now sistema-chamados-agent.timer
  systemctl start sistema-chamados-agent.service || true
  echo "Agente instalado com systemd timer: inicializacao e a cada 6 horas."
else
  cron_file="/etc/cron.d/sistema-chamados-agent"
  cat > "$cron_file" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
@reboot root /usr/bin/python3 $INSTALL_DIR/agent.py $CONFIG_FILE >> $LOG_FILE 2>&1
0 */6 * * * root /usr/bin/python3 $INSTALL_DIR/agent.py $CONFIG_FILE >> $LOG_FILE 2>&1
EOF
  chmod 0644 "$cron_file"
  /usr/bin/python3 "$INSTALL_DIR/agent.py" "$CONFIG_FILE" >> "$LOG_FILE" 2>&1 || true
  echo "Agente instalado com cron: inicializacao e a cada 6 horas."
fi

cat > "$INSTALL_DIR/uninstall.sh" <<'EOF'
#!/bin/sh
set -eu
if [ "$(id -u)" != "0" ]; then
  echo "Execute como root: sudo sh /opt/sistema-chamados-agent/uninstall.sh"
  exit 1
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl disable --now sistema-chamados-agent.timer >/dev/null 2>&1 || true
  rm -f /etc/systemd/system/sistema-chamados-agent.service /etc/systemd/system/sistema-chamados-agent.timer
  systemctl daemon-reload >/dev/null 2>&1 || true
fi
rm -f /etc/cron.d/sistema-chamados-agent
rm -rf /opt/sistema-chamados-agent /etc/sistema-chamados-agent
echo "Agente Linux removido com sucesso."
EOF
chmod 0755 "$INSTALL_DIR/uninstall.sh"

echo "Instalacao concluida."
echo "Log: $LOG_FILE"
echo "Desinstalar: sudo sh $INSTALL_DIR/uninstall.sh"
