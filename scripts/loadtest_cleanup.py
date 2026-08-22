# Removes what a load run leaves behind: bot participants, their answers, and any
# session that ends up with no real players. Run it on the bench host after a ramp.
#
# IPython's autoindent mangles indented blocks pasted into `bench console`, so this
# has to be exec'd from the file rather than piped in as source:
#   echo 'exec(open("apps/quizzly/scripts/loadtest_cleanup.py").read())' \
#     | bench --site SITE console
#
# env:
#   QZ_CLEANUP_PREFIXES  comma-separated nickname prefixes (default bot,probe,preflight,tmp)
#   QZ_CLEANUP_APPLY     1 to actually delete; anything else only reports

import os

import frappe

prefixes = os.environ.get("QZ_CLEANUP_PREFIXES", "bot,probe,preflight,tmp").split(",")
apply_changes = os.environ.get("QZ_CLEANUP_APPLY") == "1"

participants = []
for prefix in prefixes:
	participants += frappe.get_all(
		"QZ Participant",
		filters={"nickname": ["like", f"{prefix}%"]},
		fields=["name", "session", "nickname"],
	)

if not participants:
	print("nothing to clean")
else:
	bot_sessions = {row.session for row in participants}
	bot_names = {row.name for row in participants}

	# a session is only disposable when every player in it was synthetic
	real_counts = frappe.get_all(
		"QZ Participant",
		filters={"session": ["in", list(bot_sessions)]},
		fields=["session", "count(name) as total"],
		group_by="session",
	)
	total_by_session = {row.session: row.total for row in real_counts}
	bots_by_session = {}
	for row in participants:
		bots_by_session[row.session] = bots_by_session.get(row.session, 0) + 1

	disposable = [s for s in bot_sessions if bots_by_session[s] == total_by_session.get(s)]
	mixed = sorted(bot_sessions - set(disposable))

	answers = frappe.db.count("QZ Answer", {"participant": ["in", list(bot_names)]})
	print(f"bot participants: {len(bot_names)}  answers: {answers}")
	print(f"sessions fully synthetic: {len(disposable)}  sessions with real players too: {len(mixed)}")
	for session in mixed:
		print(f"  keeping session {session} ({bots_by_session[session]}/{total_by_session[session]} synthetic)")

	if not apply_changes:
		print("\ndry run — set QZ_CLEANUP_APPLY=1 to delete")
	else:
		frappe.db.delete("QZ Answer", {"participant": ["in", list(bot_names)]})
		frappe.db.delete("QZ Participant", {"name": ["in", list(bot_names)]})
		for session in disposable:
			frappe.cache.srem("qz:active_sessions", session)
			frappe.delete_doc("QZ Session", session, force=True, ignore_permissions=True)
		frappe.db.commit()
		print(f"\ndeleted {len(bot_names)} participants, {answers} answers, {len(disposable)} sessions")
