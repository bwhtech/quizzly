app_name = "quizzly"
app_title = "Quizzly"
app_publisher = "Gajendra Nishad"
app_description = "Real-time multiplayer quiz platform"
app_email = "gajendra@bwh.tech"
app_license = "mit"

add_to_apps_screen = [
	{
		"name": "quizzly",
		"logo": "/assets/quizzly/images/quizzly-logo.svg",
		"title": "Quizzly",
		"route": "/quizzly",
	}
]

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

fixtures = [{"dt": "Role", "filters": [["name", "in", ["Quiz Host"]]]}]

website_route_rules = [
	{"from_route": "/quizzly/<path:app_path>", "to_route": "quizzly"},
]

export_python_type_annotations = True
require_type_annotated_api_methods = True
