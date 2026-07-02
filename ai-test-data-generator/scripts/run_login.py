"""End-to-end demo: feed the KVB AD-login spec through the generator and write
every export to disk. Runs offline via the rule-based engine (no API key)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "sample_data" / "kvb_login_request.json"
OUT = ROOT / "results" / "kvb_login"
OUT.mkdir(parents=True, exist_ok=True)

client = TestClient(create_app())
payload = json.loads(REQUEST.read_text(encoding="utf-8"))
resp = client.post("/api/generate", json=payload)
resp.raise_for_status()
gen = resp.json()["generated"]

# Summary of the six artifact categories.
print(f"generated_by_ai : {gen['generated_by_ai']}")
print(f"positive        : {len(gen['positive'])}")
print(f"negative        : {len(gen['negative'])}")
print(f"boundary_values : {len(gen['boundary_values'])}")
print(f"partitions      : {len(gen['equivalence_partitions'])}")
print(f"api_payloads    : {len(gen['api_payloads'])}")
print(f"seed sql rows   : {len(gen['seed_data']['sql'])}")

# Write each export to its conventional filename.
exports = gen["exports"]
files = {
    "generated_api_tests.robot": exports["robot_framework"],
    "generated_api_test.py": exports["pytest"],
    "generated_api.spec.ts": exports["playwright"],
    "generated_api_checks.py": exports["python"],
}
for name, content in files.items():
    (OUT / name).write_text(content, encoding="utf-8")
    print(f"wrote {OUT / name}")
