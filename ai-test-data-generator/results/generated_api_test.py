"""Auto-generated API tests by the AI Test Data Generator.

Target: POST /api/v1/users
Run:  pip install pytest requests  &&  pytest generated_api_test.py
Set BASE_URL to point at your environment.
"""

import json
import os

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

_CASES = json.loads(r'''[
  {
    "name": "positive_1",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 201,
    "kind": "positive"
  },
  {
    "name": "positive_2",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user1@example.com",
      "username": "username",
      "password": "password",
      "age": 19,
      "role": "admin"
    },
    "expected_status": 201,
    "kind": "positive"
  },
  {
    "name": "positive_3",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user2@example.com",
      "username": "username",
      "password": "password",
      "age": 20,
      "role": "editor"
    },
    "expected_status": 201,
    "kind": "positive"
  },
  {
    "name": "negative_email_1",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "username": "username",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_email_2",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "not-an-email",
      "username": "username",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_3",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_4",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "us",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_5",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "usernamexxxxxxxxxxxxx",
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_6",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": 1234567,
      "password": "password",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_password_7",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_password_8",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "passwor",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_password_9",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "passwordxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_password_10",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": 1234567,
      "age": 18,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_age_11",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_age_12",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "age": 17,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_age_13",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "age": 121,
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_age_14",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "age": "not-a-number",
      "role": "user"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_role_15",
    "method": "POST",
    "path": "/api/v1/users",
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "body": {
      "email": "user0@example.com",
      "username": "username",
      "password": "password",
      "age": 18,
      "role": "__not_a_valid_option__"
    },
    "expected_status": 400,
    "kind": "negative"
  }
]''')

@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_api(case):
    kwargs = {"headers": case["headers"]}
    if case["method"] in ("POST", "PUT", "PATCH"):
        kwargs["json"] = case["body"]
    resp = requests.request(case["method"], BASE_URL + case["path"], **kwargs)
    assert resp.status_code == case["expected_status"], (
        f"{case['name']}: expected {case['expected_status']}, got {resp.status_code} "
        f"({resp.text[:200]})"
    )
