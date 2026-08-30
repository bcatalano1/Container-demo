import json
import os
from typing import Any, Dict

import boto3
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
    allow_origins=["*"],
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
            "user_email": request.user_email
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
def get_recipes(start_recipe_id: str = None, limit: int = 10) -> Any:
    """Fetch recent sourdough recipes from DynamoDB."""
    scan_kwargs: Dict[str, Any] = {"Limit": limit}
    if start_recipe_id:
        scan_kwargs["ExclusiveStartKey"] = {"recipe_id": start_recipe_id}
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table('SourdoughRecipes')
    response = table.scan(**scan_kwargs)
    return { "items": response.get('Items', []),
            "next_key": response.get('LastEvaluatedKey', {}).get('recipe_id') }