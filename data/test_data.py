from __future__ import annotations

from typing import Any


class Currency:
    ILS = "ILS"


class ChargeMethod:
    """PayPlus charge_method values. 1 charges the card immediately (J4)."""

    CHARGE = 1


class PaymentAmounts:
    VALID = 10
    ZERO = 0
    UI = 10
    E2E = 50
    PARAMETRIZED = (10, 99.99, 500)


class SandboxCard:
    """Published PayPlus sandbox card that approves a charge.

    The docs print the number as 5326-1402-8077-9844. The payment field
    accepts the digits and formats them itself.
    """

    NUMBER = "5326140280779844"
    EXPIRY_MONTH = "05"
    EXPIRY_YEAR = "30"
    CVV = "000"
    HOLDER_NAME = "Test User"
    PAYMENTS = "1"


class ApiStatus:
    SUCCESS = "success"
    ERROR = "error"
    APPROVED = "000"


class PaymentMessages:
    MISSING_PAGE_UID = "not-authorize-missing-payment-page-uid"
    SUCCESS_HEADING = "העסקה בוצעה בהצלחה"


def build_generate_link_payload(
    *,
    amount: int | float,
    payment_page_uid: str | None,
    more_info: str | None = None,
    include_payment_page_uid: bool = True,
) -> dict[str, Any]:
    """Body for PaymentPages/generateLink.

    Emails stay off so test charges do not notify a customer. 3-D Secure
    stays off so the sandbox card can be charged without a challenge.
    The card-holder id field is hidden so the UI flow does not depend on
    an Israeli id checksum. ``more_info`` must stay within PayPlus' 19
    character limit when it is sent.
    """
    payload: dict[str, Any] = {
        "amount": amount,
        "currency_code": Currency.ILS,
        "charge_method": ChargeMethod.CHARGE,
        "sendEmailApproval": False,
        "sendEmailFailure": False,
        "language_code": "he",
        "hide_identification_id": True,
        "secure3d": {"activate": False},
    }
    if include_payment_page_uid:
        if not payment_page_uid:
            raise ValueError("payment_page_uid is required to build a payment link payload.")
        payload["payment_page_uid"] = payment_page_uid
    if more_info is not None:
        payload["more_info"] = more_info
    return payload


def build_view_transaction_payload(
    *,
    transaction_uid: str | None = None,
    more_info: str | None = None,
) -> dict[str, str]:
    """Body for Transactions/View. One of the two lookup keys is required."""
    payload: dict[str, str] = {}
    if transaction_uid:
        payload["transaction_uid"] = transaction_uid
    if more_info:
        payload["more_info"] = more_info
    if not payload:
        raise ValueError("transaction_uid or more_info is required to view a transaction.")
    return payload
