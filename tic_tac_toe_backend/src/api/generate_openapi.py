import json
import os

from src.api.main import app

"""
Utility to regenerate the OpenAPI spec for the backend.

Run with:
    python -m src.api.generate_openapi

The output is written to interfaces/openapi.json
"""

# Get the OpenAPI schema from the running app definition
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
