#!/usr/bin/env python3
"""
SynoSmartInfo Socket Client
============================
Thin client called by api.cgi to communicate with the smart_helper daemon.

Usage:
    python3 smart_client.py <action> [option]

Writes a single JSON object to stdout and exits.

Exit codes:
    0 — response received (check "success" field in JSON for logical result)
    1 — communication error (JSON with "success": false also written to stdout)
"""

import json
import os
import socket
import sys

SOCKET_PATH = "/var/packages/Synosmartinfo/var/helper.sock"
TIMEOUT     = 260  # slightly longer than helper's max scan timeout (240 s)
MAX_RECV    = 2 * 1024 * 1024  # 2 MB — generous upper bound for SMART output


def err_response(message: str) -> str:
    return json.dumps({"success": False, "output": "", "error": message})


def main() -> None:
    if len(sys.argv) < 2:
        print(err_response("Usage: smart_client.py <action> [option]"))
        sys.exit(1)

    action = sys.argv[1]
    option = sys.argv[2] if len(sys.argv) > 2 else ""

    if not os.path.exists(SOCKET_PATH):
        print(err_response("Helper daemon not running (socket not found)"))
        sys.exit(1)

    request = json.dumps({"action": action, "option": option}) + "\n"

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect(SOCKET_PATH)
        s.sendall(request.encode())

        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            if len(data) > MAX_RECV:
                s.close()
                print(err_response("Response too large"))
                sys.exit(1)
            if data.endswith(b"\n"):
                break
        s.close()

        # Validate that we received well-formed JSON before forwarding
        try:
            json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(err_response("Invalid response from helper"))
            sys.exit(1)

        print(data.decode().rstrip("\n"))

    except socket.timeout:
        print(err_response("Request timed out"))
        sys.exit(1)
    except ConnectionRefusedError:
        print(err_response("Helper daemon refused connection"))
        sys.exit(1)
    except Exception as exc:
        print(err_response(str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()
