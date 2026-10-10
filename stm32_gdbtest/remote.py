"""GDB server on a stand host over SSH (ТЗ 5.18): table [remote] of the stand, keys only.

The runner and GDB stay on this computer; the GDB server and the debugger are on the
stand host (for example an Orange Pi next to the boards). One SSH session starts
remote_helper.py, which takes the stand host's debugger lock and runs the server, and
forwards a local port to the server's port on the stand host's loopback interface.
The runner sends a heartbeat over the session: a link that dies without closing the
connection (Wi-Fi, cable, sleep) stops the server and frees the lock after
HEARTBEAT_TIMEOUT_S instead of when TCP gives up hours later.
"""

import base64
import json
from pathlib import Path
import re
import shutil
import threading

from stm32_gdbtest.toolchain import expand_path

HELPER = Path(__file__).with_name("remote_helper.py")
ALLOWED = {"host", "user", "port", "identity_file", "env_script", "ssh"}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
DEFAULT_ENV = "~/.local/stm32-gdbtest/env.sh"
# ST vendor ID also covers application devices; only ST-Link product IDs are debuggers.
STLINK_PRODUCTS = ["3744", "3748", "374a", "374b", "374d", "374e", "374f", "3752", "3753",
                   "3754", "3755", "3757"]
LOGS = ["jlink.log", "stlink.log"]
HEARTBEAT_INTERVAL_S = 2
HEARTBEAT_TIMEOUT_S = 15


def load(table):
    """Validate [remote]; None means a local stand."""
    if table is None:
        return None
    if not isinstance(table, dict):
        raise ValueError("[remote] must be a TOML table")
    if any("pass" in key.lower() or key.lower() in ("secret", "token") for key in table):
        raise ValueError("Passwords are not supported in [remote]; use SSH key authentication")
    if set(table) - ALLOWED:
        raise ValueError("Unknown remote setting; allowed: " + ", ".join(sorted(ALLOWED)))
    host = table.get("host", "")
    if not isinstance(host, str) or not NAME.fullmatch(host):
        raise ValueError("[remote] host must be a host name, an address or an SSH config alias")
    user = table.get("user")
    if user is not None and (not isinstance(user, str) or not NAME.fullmatch(user)):
        raise ValueError("[remote] user must be a plain account name")
    port = table.get("port", 22)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("[remote] port must be an integer between 1 and 65535")
    identity = table.get("identity_file")
    if identity is not None:
        identity = Path(expand_path(identity))
        if not identity.is_absolute() or not identity.is_file():
            raise ValueError("[remote] identity_file must be an existing absolute path to a private key")
        identity = str(identity)
    env_script = table.get("env_script")
    if env_script is not None and (not isinstance(env_script, str)
                                   or not re.fullmatch(r"(~/)?[A-Za-z0-9._/+-]+", env_script)):
        raise ValueError("[remote] env_script must be a plain POSIX path (optionally starting with ~/)")
    ssh = shutil.which(table.get("ssh", "ssh"))
    if not ssh:
        raise FileNotFoundError("SSH client not found; install OpenSSH or set [remote] ssh")
    return dict(host=host, user=user, port=port, identity_file=identity, env_script=env_script, ssh=ssh)


def ssh_command(remote, *extra):
    """Non-interactive SSH: key authentication and a known host key are mandatory."""
    command = [remote["ssh"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=3",
               "-p", str(remote["port"])]
    if remote["identity_file"]:
        command += ["-i", remote["identity_file"], "-o", "IdentitiesOnly=yes"]
    if remote["user"]:
        command += ["-l", remote["user"]]
    return command + list(extra) + [remote["host"]]


def _shell_path(path):
    return '"$HOME"/' + path[2:] if path.startswith("~/") else path


def remote_script(remote, config):
    """POSIX shell command for the stand host; base64 keeps quoting independent of the local OS."""
    code = base64.b64encode(HELPER.read_bytes()).decode("ascii")
    data = base64.b64encode(json.dumps(config).encode("utf-8")).decode("ascii")
    if remote["env_script"]:
        prefix = f". {_shell_path(remote['env_script'])} >/dev/null 2>&1 || exit 97; "
    else:
        default = _shell_path(DEFAULT_ENV)
        prefix = f"if [ -r {default} ]; then . {default} >/dev/null 2>&1; fi; "
    return (prefix + "exec python3 -c 'import base64,sys;exec(base64.b64decode(sys.argv[1]))' "
            + code + " " + data + " 2>&1")


def serve_config(identity, port, command):
    return dict(mode="serve", identity=identity, port=port, command=command, logs=LOGS,
                heartbeat_s=HEARTBEAT_TIMEOUT_S)


class Heartbeat:
    """Writes a newline to the SSH session every HEARTBEAT_INTERVAL_S until stopped (ТЗ 5.18.7)."""

    def __init__(self, stream, interval=HEARTBEAT_INTERVAL_S):
        self.stream, self.interval = stream, interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._beat, name="remote-heartbeat", daemon=True)
        self.thread.start()

    def _beat(self):
        while not self.stopped.wait(self.interval):
            try:
                self.stream.write(b"\n")
                self.stream.flush()
            except (OSError, ValueError):
                return  # the session is gone or closing

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=5)


def check_config(identity, executable):
    return dict(mode="check", identity=identity, executable=executable, stlink_products=STLINK_PRODUCTS)


def parse_marker(text, key):
    """Value of the helper marker line `STM32_GDBTEST_REMOTE <key>=...`, or None."""
    for line in text.splitlines():
        if line.startswith("STM32_GDBTEST_REMOTE " + key + "="):
            return line.split("=", 1)[1]
    return None


def check_result(text):
    value = parse_marker(text, "check")
    return json.loads(value) if value else None


def forwarding_ready(tunnel_log):
    return "Local forwarding listening on" in tunnel_log or "Local connections to" in tunnel_log


def environment_hint(code):
    return {97: "env_script could not be sourced on the stand host",
            255: "SSH failed: check the key, known_hosts entry and host"}.get(code, "")


def stand_executable_default(backend):
    return {"openocd": "openocd", "jlink": "JLinkGDBServerCLExe",
            "stlink": "ST-LINK_gdbserver", "st-util": "st-util"}[backend]

