"""Auto-generated API tests by the AI Test Data Generator.

Target: POST /api/v1/auth/adlogin
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
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": "P@ssw0rd123",
      "login_type": "AD"
    },
    "expected_status": 200,
    "kind": "positive"
  },
  {
    "name": "positive_2",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "username",
      "userpassword": "userpass",
      "login_type": "AD"
    },
    "expected_status": 200,
    "kind": "positive"
  },
  {
    "name": "positive_3",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "username",
      "userpassword": "userpass",
      "login_type": "AD"
    },
    "expected_status": 200,
    "kind": "positive"
  },
  {
    "name": "negative_username_1",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "userpassword": "P@ssw0rd123",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_2",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "us",
      "userpassword": "P@ssw0rd123",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_3",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "usernamexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "userpassword": "P@ssw0rd123",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_username_4",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": 1234567,
      "userpassword": "P@ssw0rd123",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_userpassword_5",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_userpassword_6",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": "userpas",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_userpassword_7",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": "userpasswordxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_userpassword_8",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": 1234567,
      "login_type": "AD"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_login_type_9",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": "P@ssw0rd123"
    },
    "expected_status": 400,
    "kind": "negative"
  },
  {
    "name": "negative_login_type_10",
    "method": "POST",
    "path": "/api/v1/auth/adlogin",
    "headers": {
      "Content-Type": "application/json",
      "CAPTIX-CLIENT-ID": "%{KVB_CLIENT_ID}",
      "CAPTIX-API-KEY": "%{KVB_API_KEY}",
      "app-code": "%{KVB_APP_CODE}",
      "Accept": "application/json"
    },
    "body": {
      "username": "kvb_user01",
      "userpassword": "P@ssw0rd123",
      "login_type": "__not_a_valid_option__"
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
