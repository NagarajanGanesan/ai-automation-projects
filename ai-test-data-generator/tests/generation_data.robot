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
