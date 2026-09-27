import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		redirect: () => (window.session_user === "Guest" ? "/join" : "/host"),
	},
	{ path: "/join", name: "Join", component: () => import("@/pages/Join.vue") },
	{ path: "/login", name: "Login", component: () => import("@/pages/Login.vue") },
	{ path: "/play", name: "Play", component: () => import("@/pages/Play.vue") },
	{ path: "/host", name: "Host", component: () => import("@/pages/Host.vue") },
	{
		path: "/host/profile",
		name: "Profile",
		component: () => import("@/pages/Profile.vue"),
	},
	{
		path: "/host/quizzes",
		name: "Quizzes",
		component: () => import("@/pages/QuizList.vue"),
	},
	{
		path: "/host/quizzes/:name",
		name: "QuizEditor",
		component: () => import("@/pages/QuizEditor.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/trivia-tap"),
	routes,
});

// Hosting needs a real user; guests would otherwise land on an empty quiz picker.
router.beforeEach((to) => {
	const isGuest = window.session_user === "Guest";
	if (isGuest && to.path.startsWith("/host")) {
		return { path: "/login", query: { redirect: to.fullPath } };
	}
	if (!isGuest && to.path === "/login") return "/host";
});

export default router;
