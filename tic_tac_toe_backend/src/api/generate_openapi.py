import json
import os

from src.api.main import app

# Generate OpenAPI schema from the live app, including tags and models
openapi_schema = app.openapi()

# Ensure interfaces directory exists and write the schema for other containers
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
