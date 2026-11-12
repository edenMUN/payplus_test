from __future__ import annotations

from selenium.webdriver.common.by import By


class PaymentPageLocators:
    """Locators taken from the rendered PayPlus payment page.

    The page is a Vue app and does not expose data-testid attributes.
    These ids are stable on the sandbox payment page.
    """

    CARD_HOLDER_NAME = (By.ID, "card-holder-name")
    CARD_NUMBER = (By.ID, "credit-card-input")
    EXPIRY_MONTH = (By.ID, "expiration-date-month")
    EXPIRY_YEAR = (By.ID, "expiration-date-year")
    CVV = (By.ID, "cvv-input")
    PAYMENTS = (By.ID, "payments")
    SUBMIT = (By.ID, "credit-card-submit")
    SUCCESS_MESSAGE = (By.CSS_SELECTOR, ".thank-you-page-container h1")
