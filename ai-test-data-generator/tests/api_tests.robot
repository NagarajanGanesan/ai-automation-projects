*** Settings ***
Documentation     End-to-end API tests for the AI Test Data Generator.
...               Runs offline against the FastAPI app via Starlette's TestClient
...               (no live server needed). With no API key set, the app uses the
...               deterministic rule-based engine.
Library           libraries/GeneratorClient.py
Library           Collections


*** Test Cases ***
Health Reports OK And Rule-Based Mode
    ${resp}=    Get Health
    ${code}=    Status Code    ${resp}
    Should Be Equal As Integers    ${code}    200
    ${body}=    Json Body    ${resp}
    Should Be Equal    ${body}[status]    ok
    Should Be Equal    ${body}[ai_enabled]    ${False}
