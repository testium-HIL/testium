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

def _udp_server(host, port, echo_request_first=False):
    """echo_request_first: send the raw request back before the response —
    mimics a client's own multicast query looped back to the group; the
    testium adapter must skip such request frames while waiting."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    mode = " (request echoed first)" if echo_request_first else ""
    print(f"UDP listening on {host}:{port}{mode}", flush=True)
    while True:
        data, addr = srv.recvfrom(65535)
        resp = handle(data.decode())
        if echo_request_first:
            srv.sendto(data, addr)
        srv.sendto(resp.encode(), addr)


# ── Multicast UDP ────────────────────────────────────────────────────────────

def _mcast_server(group, port, iface, reply_to_group):
    """Join `group` on `iface` and answer requests.

    reply_to_group=False: unicast reply to the sender (standard flow).
    reply_to_group=True: reply sent to (group, sender_port) — only reachable
    by clients that joined the group themselves.
    """
    import struct
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port))
    srv.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                   socket.inet_aton(group) + socket.inet_aton(iface))
    if reply_to_group:
        srv.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,
                       struct.pack("b", 1))
        srv.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                       socket.inet_aton(iface))
    mode = "group-reply" if reply_to_group else "unicast-reply"
    print(f"MCAST listening on {group}:{port} ({mode}, if {iface})", flush=True)
    while True:
        data, addr = srv.recvfrom(65535)
        resp = handle(data.decode())
        dest = (group, addr[1]) if reply_to_group else addr
        srv.sendto(resp.encode(), dest)


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

    if cfg.has_section("jsonrpc_udp_request_echo"):
        re_port = cfg.getint("jsonrpc_udp_request_echo", "port", fallback=4327)
        threading.Thread(target=_udp_server, args=("0.0.0.0", re_port, True),
                         daemon=True).start()

    if cfg.has_section("jsonrpc_multicast"):
        group = cfg.get("jsonrpc_multicast", "group")
        iface = cfg.get("jsonrpc_multicast", "iface", fallback="127.0.0.1")
        port_ucast = cfg.getint("jsonrpc_multicast", "port_unicast_reply", fallback=4324)
        port_mcast = cfg.getint("jsonrpc_multicast", "port_group_reply", fallback=4325)
        threading.Thread(target=_mcast_server,
                         args=(group, port_ucast, iface, False), daemon=True).start()
        threading.Thread(target=_mcast_server,
                         args=(group, port_mcast, iface, True), daemon=True).start()

    print("JSON-RPC echo server ready", flush=True)

    try:
        tcp_thread.join()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
