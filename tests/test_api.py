from __future__ import annotations

import allure
import pytest

from api.payplus_client import PayPlusClient
from data.test_data import (
    ApiStatus,
    PaymentAmounts,
    PaymentMessages,
    build_generate_link_payload,
)
from utils.helpers import is_api_error, results_status


@allure.title("Generate a payment link with valid data")
@pytest.mark.api
@pytest.mark.smoke
def test_generate_payment_link_with_valid_data(payplus_client: PayPlusClient) -> None:
    response = payplus_client.generate_payment_link(
        build_generate_link_payload(
            amount=PaymentAmounts.VALID,
            payment_page_uid=payplus_client.payment_page_uid,
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"]["status"] == ApiStatus.SUCCESS
    assert body["data"]["payment_page_link"]


@allure.title("Generate a payment link with amount 0")
@pytest.mark.api
def test_generate_payment_link_with_zero_amount_returns_error(
    payplus_client: PayPlusClient,
) -> None:
    response = payplus_client.generate_payment_link(
        build_generate_link_payload(
            amount=PaymentAmounts.ZERO,
            payment_page_uid=payplus_client.payment_page_uid,
        )
    )

    body = response.json()
    assert body["results"]["status"] == ApiStatus.ERROR
    assert body["data"] == {}


@allure.title("Generate a payment link without payment_page_uid")
@pytest.mark.api
def test_generate_payment_link_without_payment_page_uid_returns_error(
    payplus_client: PayPlusClient,
) -> None:
    response = payplus_client.generate_payment_link(
        build_generate_link_payload(
            amount=PaymentAmounts.VALID,
            payment_page_uid=None,
            include_payment_page_uid=False,
        )
    )

    assert is_api_error(response)
    assert response.status_code == 405
    assert PaymentMessages.MISSING_PAGE_UID in response.text


@allure.title("Generate payment links for several amounts")
@pytest.mark.api
@pytest.mark.parametrize("amount", PaymentAmounts.PARAMETRIZED)
def test_generate_payment_link_for_different_amounts(
    payplus_client: PayPlusClient,
    amount: int | float,
) -> None:
    response = payplus_client.generate_payment_link(
        build_generate_link_payload(
            amount=amount,
            payment_page_uid=payplus_client.payment_page_uid,
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert results_status(response) == ApiStatus.SUCCESS
    link = body["data"]["payment_page_link"]
    assert isinstance(link, str) and link.startswith("https://")
