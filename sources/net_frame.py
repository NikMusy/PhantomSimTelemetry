"""Share normalised :class:`Frame` snapshots over the network (Radmin-friendly).

Used by the iRacing flow so a strategist on the Radmin VPN sees the driver's
live telemetry in this same MoTeC-style UI:

    driver PC :  IRacingSource(share_port=8100)  -> FrameServer broadcasts JSON
    strategy PC: IRacingNetSource(host, 8100)     -> reconstructs the Frame

Plain TCP with newline-delimited JSON — no extra dependencies, works over the
Radmin virtual LAN. Game-agnostic: it serialises whatever Frame it is given.
"""
from __future__ import annotations

import dataclasses
import json
import socket
import threading
import time
from typing import Callable, Optional

from .base import Frame

_FIELDS = {f.name for f in dataclasses.fields(Frame)}


def frame_to_json(f: Frame) -> bytes:
    return (json.dumps(dataclasses.asdict(f), separators=(",", ":")) + "\n").encode("utf-8")


def json_to_frame(line: bytes) -> Optional[Frame]:
    try:
        d = json.loads(line)
    except Exception:
        return None
    data = {}
    for k, v in d.items():
        if k not in _FIELDS:
            continue
        data[k] = [float(x) for x in v] if isinstance(v, list) else v
    try:
        return Frame(**data)
    except Exception:
        return None


# ---------------------------------------------------------------------------
class FrameServer:
    """Broadcasts the latest Frame to every connected client at a fixed rate.

    ``get_frame`` is called on the broadcaster thread to obtain the current
    Frame (e.g. the local source's ``poll``)."""

    def __init__(self, get_frame: Callable[[], Frame], port: int = 8100, hz: float = 30.0):
        self.get_frame = get_frame
        self.port = int(port)
        self.period = 1.0 / max(5.0, hz)
        self._clients: set[socket.socket] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._srv: Optional[socket.socket] = None
        self._threads: list[threading.Thread] = []
        self._bn = 0
        self.last_error = ""

    def start(self):
        if self._threads:
            return
        self._stop.clear()
        try:
            self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._srv.bind(("0.0.0.0", self.port))
            self._srv.listen(8)
            self._srv.settimeout(0.5)
        except Exception as exc:
            self.last_error = str(exc)
            self._srv = None
            return
        self._threads = [
            threading.Thread(target=self._accept_loop, daemon=True),
            threading.Thread(target=self._broadcast_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        try:
            if self._srv:
                self._srv.close()
        except Exception:
            pass
        with self._lock:
            for c in self._clients:
                try:
                    c.close()
                except Exception:
                    pass
            self._clients.clear()
        self._threads = []

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _accept_loop(self):
        while not self._stop.is_set() and self._srv:
            try:
                conn, _addr = self._srv.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with self._lock:
                    self._clients.add(conn)
            except socket.timeout:
                continue
            except OSError:
                break

    def _broadcast_loop(self):
        while not self._stop.is_set():
            t0 = time.monotonic()
            with self._lock:
                clients = list(self._clients)
            if clients:
                try:
                    fr = self.get_frame()
                    self._bn += 1
                    keep_raw = (self._bn % 3 == 0)        # full channel dump @ ~10 Hz
                    keep_units = (self._bn % 150 == 1)     # units roughly every 5 s
                    if not keep_raw or not keep_units:
                        fr = dataclasses.replace(
                            fr,
                            raw=(fr.raw if keep_raw else {}),
                            raw_units=(fr.raw_units if keep_units else {}),
                        )
                    payload = frame_to_json(fr)
                except Exception:
                    payload = b""
                if payload:
                    dead = []
                    for c in clients:
                        try:
                            c.sendall(payload)
                        except Exception:
                            dead.append(c)
                    if dead:
                        with self._lock:
                            for c in dead:
                                self._clients.discard(c)
                                try:
                                    c.close()
                                except Exception:
                                    pass
            dt = time.monotonic() - t0
            self._stop.wait(max(0.0, self.period - dt))


# ---------------------------------------------------------------------------
class NetFrameSource:
    """Client side: connect to a :class:`FrameServer` and expose the stream as
    a normal telemetry source (``poll`` / ``is_live``)."""

    def __init__(self, host: str, port: int = 8100, game: str = "iRacing"):
        self.host = host.strip()
        self.port = int(port)
        self.name = game
        self._frame: Optional[Frame] = None
        self._frame_t = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_error = ""

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=4) as s:
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    s.settimeout(2.0)
                    self.last_error = ""
                    buf = b""
                    while not self._stop.is_set():
                        try:
                            chunk = s.recv(65536)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            f = json_to_frame(line)
                            if f is not None:
                                with self._lock:
                                    self._frame = f
                                    self._frame_t = time.monotonic()
            except Exception as exc:
                self.last_error = str(exc)
            if self._stop.is_set():
                break
            time.sleep(1.2)  # reconnect backoff

    def is_live(self) -> bool:
        with self._lock:
            f = self._frame
            age = time.monotonic() - self._frame_t
        return bool(f) and f.connected and age < 2.5

    def poll(self) -> Frame:
        with self._lock:
            f = self._frame
            age = time.monotonic() - self._frame_t
        if f is None or age > 3.0:
            return Frame(t=time.monotonic(), game=self.name)
        f.t = time.monotonic()
        return f
