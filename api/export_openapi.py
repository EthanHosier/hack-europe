"""Export OpenAPI schema to openapi.json so the frontend can generate types without running the server."""
import json
from pathlib import Path

from index import app

out = Path(__file__).parent / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2))
print(f"Wrote {out}")
