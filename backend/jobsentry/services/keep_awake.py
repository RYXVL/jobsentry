"""Keep the computer from going to sleep while the monitor is on.

Only idle sleep is prevented; the screen can still turn off, and closing a
laptop's lid still sleeps it (macOS doesn't allow overriding that).

    macOS    `caffeinate -i -w <our pid>`: built in; it also ends on its own
             if the API process dies.
    Windows  SetThreadExecutionState, held by a background thread.
    Linux    `systemd-inhibit ... sleep infinity`, where systemd is available.

Anywhere else, a warning is logged and monitoring works as normal.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading

log = logging.getLogger(__name__)

class KeepAwake:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._windows_release: threading.Event | None = None

    def start(self) -> None:
        """Start preventing sleep (does nothing if already started)."""
        if self._process is not None or self._windows_release is not None:
            return
        try:
            if sys.platform == "darwin" and shutil.which("caffeinate"):
                self._process = _spawn(["caffeinate", "-i", "-w", str(os.getpid())])
            elif sys.platform.startswith("win"):
                self._windows_release = threading.Event()
                threading.Thread(
                    target=_hold_windows_awake, args=(self._windows_release,),
                    name="keep-awake", daemon=True,
                ).start()
            elif shutil.which("systemd-inhibit"):
                self._process = _spawn([
                    "systemd-inhibit", "--what=idle:sleep", "--who=Job Sentry",
                    "--why=Monitoring for new jobs", "--mode=block", "sleep", "infinity",
                ])
            else:
                log.warning("Can't keep this computer awake here; it may sleep while monitoring")
        except OSError as e:
            log.warning("Couldn't keep this computer awake: %s", e)

    def stop(self) -> None:
        """Allow sleep again."""
        if self._process is not None:
            self._process.terminate()
            self._process = None
        if self._windows_release is not None:
            self._windows_release.set()
            self._windows_release = None

def _spawn(command: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _hold_windows_awake(release: threading.Event) -> None:
    """Windows ties "stay awake" to the calling thread, so this thread asks
    for it, waits until released, then lets the computer sleep again."""
    import ctypes

    es_continuous, es_system_required = 0x80000000, 0x00000001
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.SetThreadExecutionState(es_continuous | es_system_required)
    release.wait()
    kernel32.SetThreadExecutionState(es_continuous)