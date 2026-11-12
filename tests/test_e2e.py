from __future__ import annotations

import allure
import pytest

from api.payplus_client import PayPlusClient
from data.test_data import (
    ApiStatus,
    Currency,
    PaymentAmounts,
    PaymentMessages,
    SandboxCard,
    build_generate_link_payload,
)
from pages.payment_page import PaymentPage
from utils.helpers import (
    amounts_equal,
    payment_page_link,
    results_status,
    unique_more_info,
    wait_for_transaction,
)


@allure.title("Charge 50 ILS and confirm the transaction is approved")
@pytest.mark.e2e
@pytest.mark.smoke
def test_charge_fifty_ils_and_view_approved_transaction(
    payment_page: PaymentPage,
    payplus_client: PayPlusClient,
) -> None:
    more_info = unique_more_info()

    with allure.step(f"Generate a payment link for {PaymentAmounts.E2E} ILS"):
        response = payplus_client.generate_payment_link(
            build_generate_link_payload(
                amount=PaymentAmounts.E2E,
                payment_page_uid=payplus_client.payment_page_uid,
                more_info=more_info,
            )
        )
        assert results_status(response) == ApiStatus.SUCCESS
        link = payment_page_link(response)

    payment_page.open_payment_link(link)
    payment_page.pay(
        holder_name=SandboxCard.HOLDER_NAME,
        card_number=SandboxCard.NUMBER,
        expiry_month=SandboxCard.EXPIRY_MONTH,
        expiry_year=SandboxCard.EXPIRY_YEAR,
        cvv=SandboxCard.CVV,
        payments=SandboxCard.PAYMENTS,
    )
    assert PaymentMessages.SUCCESS_HEADING in payment_page.wait_for_success_message()

    transaction = wait_for_transaction(
        payplus_client,
        transaction_uid=payment_page.transaction_uid(),
        more_info=more_info,
    )
    assert transaction["status_code"] == ApiStatus.APPROVED
    assert amounts_equal(transaction["amount"], PaymentAmounts.E2E)
    assert transaction["currency"] == Currency.ILS
    assert transaction["more_info"] == more_info
