#!/usr/bin/env python3
"""Enter an LK/Realtek console through a client-side RAW serial agent.

The protocol-mode `sdb shell` cannot reliably deliver a key into the early LK
window: firmware boot logs create enough backpressure that ESC/q arrive only
after Linux starts.  Raw mode forwards bytes directly and is the supported path.

Prerequisites:
  1. Stop the protocol agent on the client.
  2. Start the client agent in raw mode on a TCP port reachable from the server.
  3. Power-cycle the board while this helper streams ESC.

Once `Realtek>` is seen, ESC streaming stops and stdin/stdout become a
transparent bridge to the serial console.  Ctrl+C exits this helper.
"""

import argparse
import os
import select
import socket
import sys
import time
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config/serial-debug-bridge/target"


def resolve_tcp(cli_value):
    if cli_value:
        return cli_value
    env = os.environ.get("SDB_TCP")
    if env:
        return env
    try:
        for raw in DEFAULT_CONFIG.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("SDB_TCP="):
                return line.split("=", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return "127.0.0.1:17801"


def split_host_port(spec):
    host, sep, port = spec.rpartition(":")
    if not sep or not host:
        raise argparse.ArgumentTypeError("expected HOST:PORT")
    return host, int(port)


def main():
    ap = argparse.ArgumentParser(
        description="Enter LK/Realtek console through a raw serial agent and bridge stdin/stdout")
    ap.add_argument("--tcp", metavar="HOST:PORT",
                    help="raw agent endpoint (default: SDB_TCP, config, or 127.0.0.1:17801)")
    ap.add_argument("--esc-interval", type=float, default=0.5,
                    help="seconds between ESC bytes while waiting (default: 0.5)")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="seconds to wait for Realtek> (default: 600)")
    ap.add_argument("--log", help="write the raw transcript to this file")
    args = ap.parse_args()

    if args.esc_interval <= 0 or args.timeout <= 0:
        ap.error("--esc-interval and --timeout must be positive")

    endpoint = resolve_tcp(args.tcp)
    try:
        host, port = split_host_port(endpoint)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        ap.error("invalid --tcp {!r}: {}".format(endpoint, exc))

    log = None
    if args.log:
        p = Path(args.log).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        log = p.open("wb", buffering=0)

    sock = socket.create_connection((host, port), timeout=10)
    sock.setblocking(False)
    print("RAW connected {}:{}; streaming ESC. POWER-CYCLE NOW.".format(host, port),
          flush=True)

    stdin_fd = sys.stdin.fileno()
    waiting = True
    recent = bytearray()
    next_esc = 0.0
    try:
        while True:
            now = time.monotonic()
            if waiting and now >= next_esc:
                sock.sendall(b"\x1b")
                next_esc = now + args.esc_interval

            r, _, _ = select.select([sock, stdin_fd], [], [], 0.05)
            if sock in r:
                try:
                    data = sock.recv(65536)
                except BlockingIOError:
                    data = b""
                if not data:
                    print("\nraw serial connection closed", file=sys.stderr, flush=True)
                    return 1
                os.write(sys.stdout.fileno(), data)
                if log:
                    log.write(data)
                if waiting:
                    recent.extend(data)
                    if len(recent) > 131072:
                        del recent[:-131072]
                    if b"Realtek>" in recent:
                        waiting = False
                        print("\n[RAW_LK_CONSOLE_READY] ESC stopped; stdin -> UART",
                              flush=True)

            if stdin_fd in r:
                data = os.read(stdin_fd, 4096)
                if not data:
                    return 0
                sock.sendall(data)
    except KeyboardInterrupt:
        return 130
    finally:
        sock.close()
        if log:
            log.close()


if __name__ == "__main__":
    sys.exit(main())
