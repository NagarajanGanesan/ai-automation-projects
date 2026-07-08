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

Generate Returns All Six Categories
    ${req}=    Load Sample Request
    ${resp}=    Post Generate    ${req}
    ${code}=    Status Code    ${resp}
    Should Be Equal As Integers    ${code}    200
    ${body}=    Json Body    ${resp}
    ${gen}=    Set Variable    ${body}[generated]
    Should Not Be Empty    ${gen}[positive]
    Should Not Be Empty    ${gen}[negative]
    Should Not Be Empty    ${gen}[boundary_values]
    Should Not Be Empty    ${gen}[equivalence_partitions]
    Should Not Be Empty    ${gen}[api_payloads]
    Should Not Be Empty    ${gen}[seed_data][sql]
    Should Be Equal    ${gen}[generated_by_ai]    ${False}

Generate Then Fetch Result By Id
    ${req}=    Load Sample Request
    ${resp}=    Post Generate    ${req}
    ${body}=    Json Body    ${resp}
    ${gen_id}=    Set Variable    ${body}[generation_id]
    ${resp2}=    Get Result    ${gen_id}
    ${code}=    Status Code    ${resp2}
    Should Be Equal As Integers    ${code}    200
    ${body2}=    Json Body    ${resp2}
    Should Be Equal    ${body2}[generation_id]    ${gen_id}

Generate Rejects Empty Fields
    ${req}=    Load Sample Request
    ${bad}=    With Empty Fields    ${req}
    ${resp}=    Post Generator	${bad}
    ${code}=    Status Code    ${resp}
    Should Be Equal As Integers    ${code}    400
    ${body}=    Json Body    ${resp}
    Should Be Equal    ${body}[error][code]    validation_error
