from __future__ import annotations

import allure
import pytest

from api.payplus_client import PayPlusClient
from data.test_data import (
    ApiStatus,
    PaymentAmounts,
    PaymentMessages,
    SandboxCard,
    build_generate_link_payload,
)
from pages.payment_page import PaymentPage
from utils.helpers import payment_page_link, results_status, unique_more_info


@allure.title("Pay with the sandbox card and see the success message")
@pytest.mark.ui
@pytest.mark.smoke
def test_sandbox_card_payment_shows_success_message(
    payment_page: PaymentPage,
    payplus_client: PayPlusClient,
) -> None:
    response = payplus_client.generate_payment_link(
        build_generate_link_payload(
            amount=PaymentAmounts.UI,
            payment_page_uid=payplus_client.payment_page_uid,
            more_info=unique_more_info(),
        )
    )
    assert results_status(response) == ApiStatus.SUCCESS
    link = payment_page_link(response)
    allure.attach(link, name="payment_page_link", attachment_type=allure.attachment_type.TEXT)

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
