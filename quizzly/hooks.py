app_name = "quizzly"
app_title = "Quizzly"
app_publisher = "Gajendra Nishad"
app_description = "Real-time multiplayer quiz platform"
app_email = "gajendra@bwh.tech"
app_license = "mit"
app_logo_url = "/assets/quizzly/images/quizzly-logo.svg"

add_to_apps_screen = [
	{
		"name": "quizzly",
		"logo": app_logo_url,
		"title": "Quizzly",
		"route": "/quizzly",
	}
]

website_context = {"favicon": app_logo_url}

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

fixtures = [{"dt": "Role", "filters": [["name", "in", ["Quiz Host"]]]}]

# A host may only read the participants and answers of sessions they host.
# query_conditions filters list views; has_permission guards a single document.
permission_query_conditions = {
	"QZ Participant": "quizzly.permissions.participant_query_conditions",
	"QZ Answer": "quizzly.permissions.answer_query_conditions",
}

has_permission = {
	"QZ Participant": "quizzly.permissions.owns_session_row",
	"QZ Answer": "quizzly.permissions.owns_session_row",
}

website_route_rules = [
	{"from_route": "/quizzly/<path:app_path>", "to_route": "quizzly"},
]

export_python_type_annotations = True
require_type_annotated_api_methods = True
