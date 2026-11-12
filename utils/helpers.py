from __future__ import annotations

import time
import uuid
from typing import Any

import allure
import requests

from api.payplus_client import PayPlusClient
from data.test_data import ApiStatus, build_view_transaction_payload


def unique_more_info() -> str:
    """Correlation id for GenerateLink and Transactions/View.

    PayPlus returns at most 19 characters of more_info. ``e2e`` plus 12
    hex characters stays inside that limit and is unique per test.
    """
    return f"e2e{uuid.uuid4().hex[:12]}"


def is_api_error(response: requests.Response) -> bool:
    """True when PayPlus rejected the call.

    Validation failures are not consistent: a missing payment page uid is
    HTTP 405 with a plain-text body, while an invalid amount is HTTP 200
    with ``results.status`` of ``error``.
    """
    if response.status_code >= 400:
        return True
    return results_status(response) == ApiStatus.ERROR


def results_status(response: requests.Response) -> str | None:
    try:
        status = response.json()["results"]["status"]
    except (ValueError, KeyError, TypeError):
        return None
    return str(status)


def payment_page_link(response: requests.Response) -> str:
    body = response.json()
    link = body.get("data", {}).get("payment_page_link")
    if not isinstance(link, str) or not link:
        raise AssertionError(
            f"Response did not include payment_page_link: {response.status_code} {response.text}"
        )
    return link


def amounts_equal(actual: object, expected: object, tolerance: float = 0.001) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def wait_for_transaction(
    client: PayPlusClient,
    *,
    transaction_uid: str | None = None,
    more_info: str | None = None,
    timeout_seconds: float = 20,
    interval_seconds: float = 1,
) -> dict[str, Any]:
    """Poll Transactions/View until the matching charge is visible.

    The approval page can appear before the view endpoint lists the row.
    The first call often already has it; the loop covers the short gap.
    """
    payload = build_view_transaction_payload(
        transaction_uid=transaction_uid,
        more_info=more_info,
    )
    deadline = time.monotonic() + timeout_seconds
    last_response: requests.Response | None = None

    while True:
        last_response = client.view_transaction(payload)
        transaction = _matching_transaction(
            last_response,
            transaction_uid=transaction_uid,
            more_info=more_info,
        )
        if transaction is not None:
            _attach_response(last_response)
            return transaction
        if time.monotonic() >= deadline:
            break
        time.sleep(interval_seconds)

    if last_response is not None:
        _attach_response(last_response)
    raise AssertionError(
        "Transaction was not available via Transactions/View "
        f"within {timeout_seconds:.0f}s. Last response: "
        f"{getattr(last_response, 'status_code', None)} "
        f"{getattr(last_response, 'text', '')}"
    )


def _matching_transaction(
    response: requests.Response,
    *,
    transaction_uid: str | None,
    more_info: str | None,
) -> dict[str, Any] | None:
    if results_status(response) != ApiStatus.SUCCESS:
        return None
    try:
        rows = response.json().get("data") or []
    except ValueError:
        return None
    for row in rows:
        transaction = row.get("transaction") or {}
        if transaction_uid and transaction.get("transaction_uid") == transaction_uid:
            return transaction
        if more_info and transaction.get("more_info") == more_info:
            return transaction
    return None


def _attach_response(response: requests.Response) -> None:
    allure.attach(
        response.text,
        name="view_transaction_response",
        attachment_type=allure.attachment_type.JSON,
    )
