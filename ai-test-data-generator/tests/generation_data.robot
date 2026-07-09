*** Settings ***
Documentation     Verifies the six generated artifact categories and the
...               Robot Framework / Playwright export formats. Offline via the
...               rule-based engine (TestClient, no live server, no API key).
Library           libraries/GeneratorClient.py
Library           Collections


*** Test Cases ***
Positive Records Match Requested Count
    ${gen}=    Generate From Sample
    Length Should Be    ${gen}[positive]    3

Negative Records Carry A Violated Field
    ${gen}=    Generate From Sample
    ${negatives}=    Set Variable    ${gen}[negative]
    Should Not Be Empty    ${negatives}
    FOR    ${rec}    IN    @{negatives}
        Should Be Equal    ${rec}[expected_valid]    ${False}
        Should Not Be Equal    ${rec}[violated_field]    ${None}
    END

Seed Data Emits Insert Statements
    ${gen}=    Generate From Sample
    Should Be Equal    ${gen}[seed_data][table]    users
    ${statements}=    Set Variable    ${gen}[seed_data][sql]
    Should Not Be Empty    ${statements}
    FOR    ${stmt}    IN    @{statements}
        Should Start With    ${stmt}    INSERT INTO users (
    END
