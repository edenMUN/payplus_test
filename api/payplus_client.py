from __future__ import annotations

from typing import Any

import allure
import requests

from api.base_client import BaseApiClient


class PayPlusClient(BaseApiClient):
    """PayPlus REST client.

    Every call sends the api-key and secret-key headers required by the
    sandbox. Paths are the v1.0 routes under ``API_BASE_URL``.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        secret_key: str,
        payment_page_uid: str,
        timeout: float = 30,
    ) -> None:
        super().__init__(
            base_url,
            headers={"api-key": api_key, "secret-key": secret_key},
            timeout=timeout,
        )
        self.payment_page_uid = payment_page_uid

    @allure.step("Generate a PayPlus payment link")
    def generate_payment_link(self, payload: dict[str, Any]) -> requests.Response:
        return self.post("PaymentPages/generateLink", json=payload)

    @allure.step("View PayPlus transactions")
    def view_transaction(self, payload: dict[str, Any]) -> requests.Response:
        return self.post("Transactions/View", json=payload)
