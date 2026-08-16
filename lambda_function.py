import json


def lambda_handler(event, context):
    """Adjust sourdough hydration for high-altitude baking.

    Expects event payload to contain:
    - base_hydration: percentage value (e.g., 75)
    - elevation: feet above sea level (e.g., 5000)
    """
    base_hydration = float(event.get("base_hydration", 0))
    elevation = float(event.get("elevation", 0))

    adjustment_per_1000_feet = 1.5
    added_water_percentage = (elevation / 1000.0) * adjustment_per_1000_feet
    final_hydration = base_hydration + added_water_percentage

    response_body = {
        "base_hydration": base_hydration,
        "elevation": elevation,
        "added_water_percentage": added_water_percentage,
        "final_hydration": final_hydration,
    }

    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(response_body),
    }

    return response
