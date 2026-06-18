"""UDP listener running on a background QThread.

Binds a UDP socket, receives F1 25 datagrams, parses them and emits a Qt
signal per packet so the GUI thread can update the data store safely.
"""
import socket

from PyQt6.QtCore import QThread, pyqtSignal

from . import packets


class UdpListener(QThread):
    # (packetId, parsed_object_or_None, header)
    packet = pyqtSignal(int, object, object)
    status = pyqtSignal(str)            # human readable status text
    error = pyqtSignal(str)

    def __init__(self, port=20777, host="0.0.0.0", parent=None):
        super().__init__(parent)
        self.port = port
        self.host = host
        self._running = False
        self._sock = None

    def run(self):
        self._running = True
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
            except OSError:
                pass
            self._sock.bind((self.host, self.port))
            self._sock.settimeout(0.5)
        except OSError as exc:
            self.error.emit(f"Не удалось открыть порт {self.port}: {exc}")
            self._running = False
            return

        self.status.emit(f"Слушаю UDP {self.host}:{self.port}")
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                continue
            try:
                parsed = packets.parse_packet(data)
            except Exception:
                continue
            if parsed is None:
                continue
            pid, obj, header = parsed
            self.packet.emit(pid, obj, header)

        try:
            if self._sock:
                self._sock.close()
        except OSError:
            pass
        self.status.emit("Остановлено")

    def stop(self):
        self._running = False
        self.wait(1500)
