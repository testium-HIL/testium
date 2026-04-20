#!/usr/bin/env python3
"""JSON-RPC echo server for the testium validation suite.

Listens on TCP (newline-delimited JSON) and UDP.
Supports JSON-RPC 1.0 and 2.0.

Handlers:
  echo(*args)  -> [args, {}]
  <unknown>    -> error {code: -32000, message: "function not found"}

Usage:
  python3 jrpc_echo_server.py -c jrpces.ini
"""
import argparse
import configparser
import json
import socket
import sys
import threading


def _dispatch(method, params):
    if method == "echo":
        if not isinstance(params, list):
            params = [params]
        return True, [params, {}]
    return False, {"code": -32000, "message": "function not found"}


def _build_response(req, success, data):
    req_id = req.get("id", None)
    if req.get("jsonrpc") == "2.0":
        if success:
            return {"jsonrpc": "2.0", "result": data, "id": req_id}
        else:
            return {"jsonrpc": "2.0", "error": data, "id": req_id}
    else:
        if success:
            return {"result": data, "error": None, "id": req_id}
        else:
            return {"result": None, "error": data, "id": req_id}


def handle(raw: str) -> str:
    try:
        req = json.loads(raw)
        method = req.get("method", "")
        params = req.get("params", [])
        success, data = _dispatch(method, params)
        return json.dumps(_build_response(req, success, data))
    except Exception as exc:
        return json.dumps({"result": None, "error": {"code": -32700, "message": str(exc)}, "id": None})


# ── TCP ──────────────────────────────────────────────────────────────────────

def _handle_tcp_client(conn):
    buf = b""
    with conn:
        conn.settimeout(5.0)
        while True:
            try:
                chunk = conn.recv(4096)
            except (socket.timeout, ConnectionResetError, OSError):
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if line:
                    resp = handle(line.decode())
                    conn.sendall((resp + "\n").encode())


def _tcp_server(host, port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    srv.settimeout(1.0)
    print(f"TCP listening on {host}:{port}", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        threading.Thread(target=_handle_tcp_client, args=(conn,), daemon=True).start()


# ── UDP ──────────────────────────────────────────────────────────────────────

def _udp_server(host, port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    print(f"UDP listening on {host}:{port}", flush=True)
    while True:
        data, addr = srv.recvfrom(65535)
        resp = handle(data.decode())
        srv.sendto(resp.encode(), addr)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JSON-RPC echo server")
    parser.add_argument("-c", "--config", required=True, help="Path to .ini config file")
    args = parser.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(args.config)

    tcp_host = cfg.get("jsonrpc_tcp", "host", fallback="0.0.0.0")
    tcp_port = cfg.getint("jsonrpc_tcp", "port", fallback=4321)
    udp_host = cfg.get("jsonrpc_udp", "host", fallback="0.0.0.0")
    udp_port = cfg.getint("jsonrpc_udp", "port", fallback=4323)

    tcp_thread = threading.Thread(target=_tcp_server, args=(tcp_host, tcp_port), daemon=True)
    udp_thread = threading.Thread(target=_udp_server, args=(udp_host, udp_port), daemon=True)
    tcp_thread.start()
    udp_thread.start()

    print("JSON-RPC echo server ready", flush=True)

    try:
        tcp_thread.join()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
