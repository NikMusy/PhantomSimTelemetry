"""Live Telemetry — a real-time data-logger worksheet for Le Mans Ultimate and
F1 25.

On launch you pick the game:
  * LMU   — connect over the network (Radmin IP + port) to an LMU Pit Wall
            server, or read this PC's rF2 shared memory directly.
  * F1 25 — listen for the game's UDP telemetry (default port 20777).

Run:
    python main.py              # show the start screen
    python main.py --demo       # skip the picker, synthetic data preview
"""
from __future__ import annotations

import argparse
import sys

from PyQt6 import QtWidgets

from ui.mainwindow import MainWindow
from ui.start_screen import StartScreen


class DemoManager:
    """Minimal manager wrapping the synthetic source for --demo."""

    def __init__(self):
        from sources.demo_source import DemoSource
        self.src = DemoSource()

    def start(self): self.src.start()

    def stop(self): self.src.stop()

    def poll(self): return self.src.poll()

    def status(self): return {"lmu": False, "f1": False, "active": "DEMO"}


def main():
    ap = argparse.ArgumentParser(description="Live Telemetry for LMU / F1 25")
    ap.add_argument("--demo", action="store_true", help="feed synthetic data")
    args = ap.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Live Telemetry")
    app.setStyle("Fusion")

    if args.demo:
        manager = DemoManager()
    else:
        start = StartScreen()
        if start.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        manager = start.manager

    win = MainWindow(manager=manager)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
