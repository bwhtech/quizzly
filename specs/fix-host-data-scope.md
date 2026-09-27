# Fix: a host sees only their own games

## Problem

Quizzes and sessions are private through `if_owner` rules. Players
(`TT Participant`) and answers (`TT Answer`) are not: `Quiz Host` reads them with
no owner check, so any host can list every player and answer from every host's
games through desk or `frappe.client`. An owner check cannot fix it, because
guests create those rows.

This matters once anyone can sign up as a host.

## Fix

`permission_query_conditions` and `has_permission` hooks on both DocTypes: a
host sees a row when they host its session. System Manager sees everything.
Game APIs read these rows with `frappe.get_all` and are unaffected.

## Check

Two hosts. The second cannot list or open the first host's quiz, session,
players or answers; the first still can.
