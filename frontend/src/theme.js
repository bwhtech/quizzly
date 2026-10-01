import { ref, watch } from "vue";

// A bound path: a static <img src> makes Vite try to bundle a file Frappe serves.
export const LOGO_URL = "/assets/trivia_tap/images/trivia-tap-logo.png";

const STORAGE_KEY = "trivia-tap-theme";
const NEXT = { auto: "light", light: "dark", dark: "auto" };

// "auto" leaves the attribute off entirely, so index.css falls through to
// prefers-color-scheme. The other two pin it against the OS.
export const theme = ref(localStorage.getItem(STORAGE_KEY) || "auto");

export function cycleTheme() {
	theme.value = NEXT[theme.value] || "auto";
}

watch(
	theme,
	(value) => {
		if (value === "auto") {
			localStorage.removeItem(STORAGE_KEY);
			delete document.documentElement.dataset.theme;
		} else {
			localStorage.setItem(STORAGE_KEY, value);
			document.documentElement.dataset.theme = value;
		}
	},
	{ immediate: true }
);
