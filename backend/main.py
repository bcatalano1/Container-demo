import json
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class CalculationRequest(BaseModel):
    base_hydration: float
    elevation: float
    user_id: str
    user_email: str


app = FastAPI(title="Sourdough Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/calculate")
def calculate(request: CalculationRequest):
    try:
        lambda_client = boto3.client("lambda", region_name="us-east-1")

        payload = {
            "base_hydration": request.base_hydration,
            "elevation": request.elevation,
            "user_id": request.user_id,
            "user_email": request.user_email,
        }

        response = lambda_client.invoke(
            FunctionName="SourdoughCalculator",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code != 200:
            raise RuntimeError(f"Lambda invocation failed with HTTP status {status_code}")

        payload_bytes = response.get("Payload")
        if payload_bytes is None:
            raise RuntimeError("Lambda invocation returned no payload")

        response_payload = payload_bytes.read()
        if not response_payload:
            raise RuntimeError("Lambda invocation returned an empty payload")

        try:
            parsed = json.loads(response_payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Lambda response payload was not valid JSON") from exc

        if isinstance(parsed, dict) and "body" in parsed and isinstance(parsed["body"], str):
            try:
                parsed["body"] = json.loads(parsed["body"])
            except json.JSONDecodeError:
                pass

        return parsed

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to invoke AWS Lambda",
                "message": str(exc),
            },
        ) from exc


@app.get("/recipes")
def get_recipes(start_recipe_id: Optional[str] = None, limit: int = 10, user_id: Optional[str] = None) -> Any:
    """Fetch the current user's sourdough recipes from the user-specific DynamoDB index."""
    if not user_id:
        return {"items": [], "next_key": None}

    desired_limit = max(1, int(limit))
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("SourdoughRecipes")

    query_kwargs: Dict[str, Any] = {
        "IndexName": "UserRecipesIndex",
        "KeyConditionExpression": Key("user_id").eq(user_id),
        "Limit": desired_limit,
    }

    if start_recipe_id:
        query_kwargs["ExclusiveStartKey"] = {"user_id": user_id, "recipe_id": start_recipe_id}

    try:
        response = table.query(**query_kwargs)
        return {
            "items": response.get("Items", [])[:desired_limit],
            "next_key": response.get("LastEvaluatedKey", {}).get("recipe_id"),
        }
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"ResourceNotFoundException", "ValidationException"}:
            return {"items": [], "next_key": None}
        raise