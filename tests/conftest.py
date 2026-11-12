from __future__ import annotations

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from pages.payment_page import PaymentPage


@pytest.fixture
def payment_page(driver: WebDriver) -> PaymentPage:
    """Build a payment page for this test's browser.

    The link is created per test, so the fixture does not open a URL.
    """
    return PaymentPage(driver)
