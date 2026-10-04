"""Pure helpers for the Jira tests.

A module of their own rather than living in ``conftest.py``: importing a
conftest from a test creates a second module instance, and these need to be
importable for ``parametrize`` as well as from fixtures.
"""

from __future__ import annotations

import json

import httpx

from ai_qa.config import Settings

JIRA_SITE = "https://jira.example.invalid"
SENTINEL_TOKEN = "SENTINEL-token-value"


def issue_payload(key: str = "TC-345", **overrides: object) -> dict:
    """A v3 issue response, with an ADF description - the real shape."""
    payload = {
        "key": key,
        "fields": {
            "summary": "Checkout rejects an expired card",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Bug"},
            "labels": ["checkout", "payments"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "An expired card must be refused."}],
                    },
                    {
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Show the reason"}],
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
        },
    }
    payload["fields"].update(overrides)  # type: ignore[union-attr]
    return payload


def jira_settings(**overrides: object) -> Settings:
    base = {
        "base_url": "https://example.com",
        "jira_base_url": JIRA_SITE,
        "jira_email": "engineer@example.com",
        "jira_api_token": SENTINEL_TOKEN,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def json_response(status: int, body: object, **headers: str) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body), headers={"content-type": "application/json", **headers})
