/**
 * The alert chime, played with Web Audio: a rising three-note arpeggio,
 * twice, about 4 seconds in all. The backend plays the same chime when no
 * tab is open (backend/jobsentry/services/sound.py).
 *
 * Browsers only allow sound after the person has interacted with the page,
 * so unlockAudio() is called on the first click or key press (see
 * AlertListener) and by "Test sound".
 */

let context: AudioContext | null = null;

function audio(): AudioContext | null {
  if (!context) {
    const Context =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Context) return null;
    context = new Context();
  }
  return context;
}

/** Allow sound from now on (call from a click or key press). */
export function unlockAudio(): void {
  void audio()?.resume();
}

/** True once the browser allows this page to play sound. */
export function audioReady(): boolean {
  return context?.state === "running";
}

const NOTES = [659.25, 783.99, 1046.5]; // E5, G5, C6

export function playChime(): void {
  const ctx = audio();
  if (!ctx) return;
  void ctx.resume();
  const start = ctx.currentTime + 0.05;
  for (let round = 0; round < 2; round += 1) {
    NOTES.forEach((frequency, index) => {
      const at = start + round * 1.8 + index * 0.28;
      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, at);
      gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02); // quick fade in, no click
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 1.6); // slow fade out
      oscillator.connect(gain).connect(ctx.destination);
      oscillator.start(at);
      oscillator.stop(at + 1.7);
    });
  }
}