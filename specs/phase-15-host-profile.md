# Phase 15: Host profile

## Goal

A host who signed up in the SPA can fix their name and change their password
without opening desk.

## Flow

The host bar shows a profile pill (icon, plus the email on wider screens) that
opens `/host/profile`. The page has two cards:

- **Name**: first and last name, saved with `frappe.client.set_value` on the
  host's own User. Frappe lets a user write their own User and refuses anyone
  else's.
- **Password**: current, new and confirm, each with the eye button. The confirm
  check runs before the call. After a change the page reloads, because frappe
  starts a new session and the CSRF token in the page goes stale.

## `change_password(old_password, new_password)`

Logged-in, POST only, rate limited per IP. It checks the current password, then
hands over to frappe's `update_password`, which applies the password policy,
refuses a reused password and logs the user back in.

It exists because frappe's request handler clears the session cookies on any
`AuthenticationError`, and `update_password` raises exactly that for a wrong
current password. Calling it directly would log the host out for a typo. The
wrapper turns that case into a validation error.

## Tracer bullet

1. `change_password` with tests. **Feedback: a wrong current password is a
   validation error, a right one changes the password.**
2. Profile page and host bar link. **Feedback: in the browser, a wrong current
   password leaves the host logged in, a right one changes it, and the new
   password logs in.**

## Out of scope

Changing email (it is the User name), profile picture, deleting the account.
