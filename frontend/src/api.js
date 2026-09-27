import { frappeRequest } from "frappe-ui";

const HOST_ACCESS_ERROR = "Log in with a Quiz Host account to write and host quizzes.";

// A host screen that a non-host opens fails on its first call; the framework's own
// message names doctypes and permissions, which means nothing to a teacher.
export function readError(e) {
	return e.exc_type === "PermissionError" ? HOST_ACCESS_ERROR : errorText(e);
}

// Server messages are HTML (the password policy sends a <ul> of hints), and the
// screens show them as text.
export function errorText(e) {
	const html = e.messages?.[0] || e.message;
	const body = new DOMParser().parseFromString(html, "text/html").body;
	const items = [...body.querySelectorAll("li")].map((item) => item.textContent);
	return items.length ? items.join(" ") : body.textContent;
}

export function call(method, params = {}) {
	return frappeRequest({
		url: `/api/method/${method}`,
		method: "POST",
		params,
		headers: { "X-Frappe-Site-Name": window.site_name },
	});
}
