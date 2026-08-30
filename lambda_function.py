import json
import boto3
import uuid

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table('SourdoughRecipes')

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

    table.put_item(
        Item={
            'recipe_id': str(uuid.uuid4()),
            'base_hydration': str(base_hydration),
            'elevation': str(elevation),
            'added_water_percentage': str(added_water_percentage),
            'final_hydration': str(final_hydration),
            'user_id': event.get("user_id", "anonymous"),
            'user_email': event.get("user_email", "anonymous"),
        }
    )

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
