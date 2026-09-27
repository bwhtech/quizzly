# Phase 14: Log in and sign up inside the SPA

## Goal

A teacher who has never used TriviaTap opens `/trivia-tap`, makes an account, and
lands on the host screen ready to write a quiz. No trip through desk `/login`, no
admin granting a role. From there the existing flow runs: write a quiz, start a
game, share the join link or QR, play.

## Flow

```
/trivia-tap/host (guest) -> /trivia-tap/login?redirect=/host
  Log in:  email + password -> /api/method/login -> reload at redirect
  Sign up: name + email + password + confirm -> trivia_tap.auth.sign_up -> reload at redirect
```

The page reloads after either, because the boot context (`session_user`,
`csrf_token`) is rendered into the page by the server.

Each password field has an eye button to show what was typed. Sign up asks for
the password twice and stops before the call when the two differ.

The join page links hosts to the login page. A logged-in user who opens
`/login` goes straight on to the host screen.

## `sign_up(full_name, email, password)`

Guest, POST only, rate limited per IP. It follows frappe's own `sign_up`:

- Refused when Website Settings has sign up disabled.
- Refused past System Settings `max_signups_allowed_per_hour`.
- An email that already has an account gets the same generic message as frappe
  gives, so the form cannot probe which emails exist.

Unlike frappe's, it sets the password the user typed (password policy applies),
gives the `Quiz Host` role, sends no welcome email, and logs the new user in.
Frappe's `sign_up` only mails a link, which breaks "sign up and host now".

`Quiz Host` has desk access, so a new host is a System User who sees only the
TriviaTap DocTypes their role allows. This matches hosts created by hand today.

## Tracer bullet

1. `sign_up` API with tests. **Feedback: a guest call creates a Quiz Host who is
   logged in.**
2. Login page with two tabs, router guard points at it. **Feedback: a new
   account in the browser reaches the host screen, writes a quiz and starts a
   game; a phone joins by the link.**

## Out of scope

Password reset stays on desk `/login#forgot` (linked from the page). Social
login and email verification are left to frappe's own login page.
