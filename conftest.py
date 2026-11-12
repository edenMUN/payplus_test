from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import allure
import pytest
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from api.base_client import BaseApiClient
from api.payplus_client import PayPlusClient

load_dotenv(Path(__file__).resolve().parent / ".env")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom CLI options for test execution."""
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="Target environment to run tests against (e.g., dev, qa, prod)",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed browser mode (default is headless for CI)",
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is not set in the environment variables or .env file.")
    return value


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """Retrieve base URL from environment variables."""
    del request
    return _required_env("BASE_URL")


@pytest.fixture(scope="session")
def api_client(base_url: str) -> BaseApiClient:
    """Session-scoped fixture for API requests client."""
    api_url = os.getenv("API_BASE_URL", f"{base_url}/api")
    client = BaseApiClient(base_url=api_url)
    api_key = os.getenv("API_KEY")
    secret_key = os.getenv("SECRET_KEY")
    if api_key and secret_key:
        client.session.headers.update({"api-key": api_key, "secret-key": secret_key})
    return client


@pytest.fixture(scope="session")
def payplus_client(base_url: str) -> PayPlusClient:
    """Authenticated PayPlus client for payment links and transactions."""
    api_url = os.getenv("API_BASE_URL", f"{base_url}/api")
    return PayPlusClient(
        base_url=api_url,
        api_key=_required_env("API_KEY"),
        secret_key=_required_env("SECRET_KEY"),
        payment_page_uid=_required_env("PAYMENT_PAGE_UID"),
    )


@pytest.fixture
def driver(request: pytest.FixtureRequest) -> Iterator[WebDriver]:
    """
    Initialize Selenium WebDriver with ChromeDriverManager (no manual driver downloads),
    configure 1920x1080 viewport, and handle automatic teardown and Allure failure attachments.
    """
    headed = request.config.getoption("--headed")

    options = webdriver.ChromeOptions()
    if not headed:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = ChromeService(ChromeDriverManager().install())
    driver_instance = webdriver.Chrome(service=service, options=options)

    yield driver_instance

    driver_instance.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[None],
) -> Iterator[None]:
    """
    Hook to capture test results and automatically attach a screenshot
    to the Allure report if a UI test fails.
    """
    del call
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver_instance = item.funcargs.get("driver")
        if driver_instance is None:
            page = item.funcargs.get("payment_page")
            driver_instance = getattr(page, "driver", None)
        if driver_instance:
            try:
                allure.attach(
                    driver_instance.get_screenshot_as_png(),
                    name="screenshot_on_failure",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception as error:
                print(f"Failed to take screenshot for Allure report: {error}")


def _is_ci_pipeline() -> bool:
    """Skip auto-open on real CI servers, not generic CI=true (Cursor sets that locally)."""
    return any(
        os.getenv(var)
        for var in (
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "CIRCLECI",
            "JENKINS_URL",
            "TF_BUILD",
            "BUILDKITE",
        )
    )


def _open_allure_report(results_dir: str) -> None:
    allure_exe = shutil.which("allure")
    if not allure_exe:
        print("Allure command-line tool is not installed or not in PATH. Skipping auto-open.")
        return

    print("\nGenerating and opening Allure report locally...")
    command = [allure_exe, "serve", os.path.abspath(results_dir)]
    if os.name == "nt":
        subprocess.Popen(
            command,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return
    subprocess.Popen(command, start_new_session=True)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Open Allure once after the full run, including pytest-xdist controller.
    Workers have workerinput and are skipped so only one report opens.
    """
    del exitstatus
    if getattr(session.config.option, "collectonly", False):
        return
    if _is_ci_pipeline() or hasattr(session.config, "workerinput"):
        return

    results_dir = getattr(session.config.option, "allure_report_dir", None) or "allure-results"
    if os.path.exists(results_dir) and os.listdir(results_dir):
        _open_allure_report(results_dir)
