from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import allure
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from locators.locators import PaymentPageLocators
from pages.base_page import BasePage

# Inputs fail fast. Page load, submit, and the approval screen get a longer wait.
FIELD_TIMEOUT = 10
FLOW_TIMEOUT = 40


class PaymentPage(BasePage):
    """Hosted PayPlus payment page at paymentsdev.payplus.co.il."""

    def __init__(self, driver: WebDriver, timeout: int = FIELD_TIMEOUT) -> None:
        super().__init__(driver, timeout)

    @allure.step("Open payment link: {url}")
    def open_payment_link(self, url: str) -> None:
        self.open(url)
        self._until(
            EC.visibility_of_element_located(PaymentPageLocators.CARD_HOLDER_NAME),
            FLOW_TIMEOUT,
        )

    @allure.step("Fill the payment form and submit it")
    def pay(
        self,
        *,
        holder_name: str,
        card_number: str,
        expiry_month: str,
        expiry_year: str,
        cvv: str,
        payments: str,
    ) -> None:
        self.type_text(PaymentPageLocators.CARD_HOLDER_NAME, holder_name)
        self.type_text(PaymentPageLocators.CARD_NUMBER, card_number)
        self.select_by_value(PaymentPageLocators.EXPIRY_MONTH, expiry_month)
        self.select_by_value(PaymentPageLocators.EXPIRY_YEAR, expiry_year)
        self.type_text(PaymentPageLocators.CVV, cvv)
        self.select_by_value(PaymentPageLocators.PAYMENTS, payments)
        self.submit_payment()

    @allure.step("Submit the payment")
    def submit_payment(self) -> None:
        self.click(PaymentPageLocators.SUBMIT, timeout=FLOW_TIMEOUT)

    @allure.step("Wait until the payment success message is displayed")
    def wait_for_success_message(self) -> str:
        self._until(EC.url_contains("/approve/"), FLOW_TIMEOUT)
        heading = self._until(
            EC.visibility_of_element_located(PaymentPageLocators.SUCCESS_MESSAGE),
            FLOW_TIMEOUT,
        )
        return heading.text.strip()

    @allure.step("Read the transaction uid from the approval URL")
    def transaction_uid(self) -> str:
        query = parse_qs(urlparse(self.current_url()).query)
        values = query.get("transaction_uid", [])
        if not values or not values[0]:
            raise AssertionError(
                "The approval page URL does not include transaction_uid: "
                f"{self.current_url()}"
            )
        return values[0]
