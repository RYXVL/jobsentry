"""The alert chime, played by this computer when no Job Sentry tab is open.

The chime (about 4 seconds: a rising three-note arpeggio, twice) is
generated once as a WAV file in the temp folder, so there's no audio file
to ship. The frontend plays the same chime with Web Audio (utils/chime.ts).

    macOS    afplay (built in)
    Windows  winsound (part of Python)
    Linux    paplay or aplay, if installed
"""

from __future__ import annotations

import logging
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path

log = logging.getLogger(__name__)

SAMPLE_RATE = 22_050
#: (start time in seconds, frequency in Hz): E5, G5, C6, then again.
NOTES = [(round_start + offset, freq)
         for round_start in (0.0, 1.8)
         for offset, freq in ((0.0, 659.25), (0.28, 783.99), (0.56, 1046.5))]
NOTE_SECONDS = 1.6
DURATION = 4.1

def play_chime() -> bool:
    """Play the chime without waiting for it to finish. Returns whether a
    player was found."""
    try:
        path = _chime_file()
        if sys.platform == "darwin" and shutil.which("afplay"):
            _spawn(["afplay", str(path)])
        elif sys.platform.startswith("win"):
            import winsound

            threading.Thread(
                target=winsound.PlaySound, args=(str(path), winsound.SND_FILENAME), daemon=True,
            ).start()
        elif player := (shutil.which("paplay") or shutil.which("aplay")):
            _spawn([player, str(path)])
        else:
            log.warning("No audio player found to play the alert chime")
            return False
        return True
    except OSError as e:
        log.warning("Couldn't play the alert chime: %s", e)
        return False

def _chime_file() -> Path:
    """The chime as a WAV file, written the first time it's needed."""
    path = Path(tempfile.gettempdir()) / "jobsentry-chime.wav"
    if not path.exists():
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(_chime_samples())
    return path

def _chime_samples() -> bytes:
    """Sine-wave notes that fade out, mixed and kept below full volume."""
    total = int(DURATION * SAMPLE_RATE)
    mix = [0.0] * total
    for start, freq in NOTES:
        first = int(start * SAMPLE_RATE)
        for i in range(int(NOTE_SECONDS * SAMPLE_RATE)):
            if first + i >= total:
                break
            t = i / SAMPLE_RATE
            attack = min(1.0, t / 0.02)               # 20 ms fade in, no click
            mix[first + i] += math.sin(2 * math.pi * freq * t) * attack * math.exp(-3.0 * t)
    peak = max(abs(sample) for sample in mix) or 1.0
    scale = 0.6 * 32767 / peak
    return b"".join(struct.pack("<h", int(sample * scale)) for sample in mix)

def _spawn(command: list[str]) -> None:
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)