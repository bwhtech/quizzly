app_name = "trivia_tap"
app_title = "TriviaTap"
app_publisher = "Gajendra Nishad"
app_description = "Real-time multiplayer quiz platform"
app_email = "gajendra@bwh.tech"
app_license = "mit"

add_to_apps_screen = [
	{
		"name": "trivia_tap",
		"logo": "/assets/trivia_tap/images/trivia-tap-logo.png",
		"title": "TriviaTap",
		"route": "/trivia-tap",
	}
]

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

fixtures = [{"dt": "Role", "filters": [["name", "in", ["Quiz Host"]]]}]

website_route_rules = [
	{"from_route": "/trivia-tap", "to_route": "trivia_tap"},
	{"from_route": "/trivia-tap/<path:app_path>", "to_route": "trivia_tap"},
]

export_python_type_annotations = True
require_type_annotated_api_methods = True
