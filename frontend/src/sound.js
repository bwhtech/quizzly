import { ref } from "vue";

const KEY = "tt_muted";

// Phones in a room all unmuting at once is a bad time, so players start silent
// while the host screen, which is the one plugged into speakers, starts audible.
const DEFAULT_MUTED = { host: false, player: true };

export const muted = ref(true);

let context;

export function initSound(role) {
	const stored = localStorage.getItem(KEY);
	muted.value = stored === null ? DEFAULT_MUTED[role] : stored === "1";
}

export function toggleMute() {
	muted.value = !muted.value;
	localStorage.setItem(KEY, muted.value ? "1" : "0");
	if (!muted.value) playCue("submit");
}

const CUES = {
	tick: { notes: [880], type: "square", noteMs: 60, gain: 0.05 },
	submit: { notes: [660, 880], type: "sine", noteMs: 70, gain: 0.08 },
	correct: { notes: [523, 659, 784], type: "sine", noteMs: 110, gain: 0.1 },
	wrong: { notes: [311, 233], type: "sawtooth", noteMs: 160, gain: 0.06 },
	podium: { notes: [523, 659, 784, 1047, 1319], type: "triangle", noteMs: 150, gain: 0.1 },
};

export function playCue(name) {
	const cue = CUES[name];
	if (muted.value || !cue) return;

	// Constructed on the first cue, which only ever follows a tap, so autoplay
	// policy is satisfied without tracking gestures ourselves.
	context = context || new (window.AudioContext || window.webkitAudioContext)();
	if (context.state === "suspended") context.resume();

	cue.notes.forEach((frequency, index) => {
		const start = context.currentTime + (index * cue.noteMs) / 1000;
		const end = start + cue.noteMs / 1000;

		const oscillator = context.createOscillator();
		oscillator.type = cue.type;
		oscillator.frequency.value = frequency;

		// Ramp down rather than stopping flat, which clicks.
		const envelope = context.createGain();
		envelope.gain.setValueAtTime(cue.gain, start);
		envelope.gain.exponentialRampToValueAtTime(0.0001, end);

		oscillator.connect(envelope).connect(context.destination);
		oscillator.start(start);
		oscillator.stop(end);
	});
}
