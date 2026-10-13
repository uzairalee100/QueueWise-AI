/**
 * QueueWise AI — Audio Synthesis Utility
 *
 * Synthesizes audible alert tones using standard Web Audio API.
 * Requires zero external audio assets and operates 100% offline.
 */

let audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
    if (AudioContextClass) {
      audioCtx = new AudioContextClass()
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume()
  }
  return audioCtx
}

/**
 * Play a hospital/counter announcement chime (two harmonic bells).
 * Triggered when a citizen's token is CALLED.
 */
export function playCallChime(): void {
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime

    // Tone 1: High crisp bell (D5 - 587.33 Hz)
    const osc1 = ctx.createOscillator()
    const gain1 = ctx.createGain()
    osc1.type = 'sine'
    osc1.frequency.setValueAtTime(587.33, now)
    gain1.gain.setValueAtTime(0, now)
    gain1.gain.linearRampToValueAtTime(0.4, now + 0.04)
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.6)
    osc1.connect(gain1)
    gain1.connect(ctx.destination)
    osc1.start(now)
    osc1.stop(now + 0.6)

    // Tone 2: Ascending resolve bell (A5 - 880 Hz)
    const osc2 = ctx.createOscillator()
    const gain2 = ctx.createGain()
    osc2.type = 'sine'
    osc2.frequency.setValueAtTime(880, now + 0.25)
    gain2.gain.setValueAtTime(0, now + 0.25)
    gain2.gain.linearRampToValueAtTime(0.45, now + 0.29)
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 1.1)
    osc2.connect(gain2)
    gain2.connect(ctx.destination)
    osc2.start(now + 0.25)
    osc2.stop(now + 1.1)
  } catch (err) {
    console.warn('Audio chime playback blocked or not supported:', err)
  }
}

/**
 * Play a gentle alert tone for approaching turn (position <= 2).
 */
export function playApproachingAlert(): void {
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.setValueAtTime(523.25, now) // C5
    gain.gain.setValueAtTime(0, now)
    gain.gain.linearRampToValueAtTime(0.25, now + 0.03)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(now)
    osc.stop(now + 0.4)
  } catch (err) {
    console.warn('Approaching alert audio playback blocked:', err)
  }
}

