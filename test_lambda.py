import json

from lambda_function import lambda_handler


mock_event = {
    "base_hydration": 75.0,
    "elevation": 6224,
}

response = lambda_handler(mock_event, None)
print(json.dumps(response, indent=2))
