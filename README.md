# PayPlus payment automation

Pytest project for the PayPlus sandbox. API tests create payment links with `requests`. UI tests open those links in Chrome, pay with the published sandbox card, and check the approval page. The end-to-end test does both, then reads the charge back with the View Transaction API.

## Install and configure

Python 3.10 or newer and Google Chrome are required. The Allure command line is optional. When it is on `PATH`, a local run opens the report when the suite finishes. Real CI systems (`GITHUB_ACTIONS`, `GITLAB_CI`, `CIRCLECI`, `JENKINS_URL`, `TF_BUILD`, `BUILDKITE`) do not auto-open it.

Windows:

```powershell
.\setup.ps1
```

macOS or Linux:

```bash
chmod +x setup.sh
./setup.sh
```

The setup script installs Poetry if it is missing, then runs `poetry install`. If the `poetry` executable cannot start, use `python -m poetry` in place of `poetry` in the commands below.

Create a `.env` file (setup does this from `.env.example` when `.env` is absent) and set:

| Variable | Purpose |
| --- | --- |
| `BASE_URL` | MyAccount origin. The suite requires it. Default in the example is `https://myaccountdev.payplus.co.il`. |
| `API_BASE_URL` | REST root, including the version prefix: `https://restapidev.payplus.co.il/api/v1.0`. |
| `API_KEY` | Sent as the `api-key` header. |
| `SECRET_KEY` | Sent as the `secret-key` header. |
| `PAYMENT_PAGE_UID` | Payment page the links are generated for. |

`.env` is gitignored. Do not commit keys.

## Run tests

From the project root:

```bash
poetry run pytest
```

Run tests in headed mode (visible browser):

```bash
poetry run pytest --headed
```

Run a specific test file:

```bash
poetry run pytest tests/test_ui.py
```

Run tests by marker (for example smoke tests):

```bash
poetry run pytest -m smoke
```

Only API, only UI, or only the end-to-end flow:

```bash
poetry run pytest -m api
poetry run pytest -m ui
poetry run pytest -m e2e
```

Run tests in parallel (using pytest-xdist):

```bash
poetry run pytest -n auto
```

Generate and serve the Allure report locally:

```bash
allure serve allure-results
```

A full local run already serves that report when the Allure CLI is installed. UI failures attach a screenshot.

The amount `0` API test asserts `results.status` is `error`. On this sandbox the call still returns a success link, so that test fails.

## What the tests cover

API (`tests/test_api.py`):

- A valid link returns `results.status` `success` and a `payment_page_link`.
- Amount `0` is expected to be rejected. On this sandbox it is not. See below.
- Omitting `payment_page_uid` returns HTTP 405 and `not-authorize-missing-payment-page-uid`.
- Amounts 10, 99.99, and 500 each return an `https` payment link.

UI (`tests/test_ui.py`):

- Generate a link, open it, pay with the sandbox success card, and assert the approval heading.

End to end (`tests/test_e2e.py`):

1. Generate a link for 50 ILS.
2. Open it in Chrome.
3. Fill the sandbox card.
4. Submit the payment.
5. Assert the success heading is visible.
6. Call Transactions/View with the `transaction_uid` from the approval URL (and the `more_info` sent on the link).
7. Assert `status_code` is `000`, the amount is 50, the currency is ILS, and `more_info` matches.

## Assumptions and design decisions

- The documented staging server is `https://restapidev.payplus.co.il/api/v1.0`. Generate Link is `POST /PaymentPages/generateLink`. View is `POST /Transactions/View`. Both use the `api-key` and `secret-key` headers.
- Amount `0` is asserted as an error. On this sandbox payment page GenerateLink still returns a success link for amount `0`, so `test_generate_payment_link_with_zero_amount_returns_error` fails.
- Missing `payment_page_uid` is HTTP 405 with a plain-text body, not the JSON `results` object used by other failures. `is_api_error` treats both shapes as errors.
- The approval screen is `https://paymentsdev.payplus.co.il/approve/{page_request_uid}`. Its heading is `העסקה בוצעה בהצלחה`. The route `/thanks/:uid` exists in the payment app but is not where this page lands. `language_code: "he"` is sent because this payment page stayed Hebrew when `"en"` was requested.
- The success URL carries `transaction_uid`. Generate Link only returns `page_request_uid`, which is not the charge id, so the end-to-end test reads `transaction_uid` from the approval URL and also sends a unique `more_info` (15 characters, under PayPlus' 19 character limit) so View can find the same row if the query string is ever absent.
- View can lag behind the approval page by a moment, so the client is polled for up to 20 seconds. UI synchronization uses explicit waits only.
- `charge_method` is `1` (immediate charge). `sendEmailApproval` and `sendEmailFailure` are `false`. `secure3d.activate` is `false` so the sandbox card is not sent into a challenge. `hide_identification_id` is `true` so the form does not ask for an Israeli id.
- One payment installment is selected so the full amount is charged. The card is the sandbox success card from the PayPlus docs: number `5326-1402-8077-9844`, expiry `05/30`, CVV `000`.
- Credentials and the payment page uid stay in `.env`. Payloads, the sandbox card, and expected messages stay in `data/test_data.py`.
- Browsers are headless unless `--headed` is passed. ChromeDriver is installed by webdriver-manager. Each test gets its own browser. The API client is session-scoped and uses one `requests.Session`.
