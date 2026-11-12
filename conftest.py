from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import allure
import pytest
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from api.payplus_client import PayPlusClient

logger = logging.getLogger(__name__)

_ENV_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_PROJECT_ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom CLI options for test execution."""
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="Environment file to load. 'dev' reads .env. Any other name reads .env.<name>.",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed browser mode (default is headless for CI)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Load the selected environment and keep browser tests on one xdist worker."""
    _load_environment(str(config.getoption("--env")))
    # pytest-xdist turns plain `-n` into `--dist load` before configure.
    # loadgroup still spreads API tests, and keeps the shared browser group
    # on one worker. Other explicit --dist values are left alone.
    numprocesses = getattr(config.option, "numprocesses", None)
    if numprocesses and getattr(config.option, "dist", None) == "load":
        config.option.dist = "loadgroup"


def pytest_itemcollected(item: pytest.Item) -> None:
    """Group browser tests before xdist copies the group name onto the node id."""
    if "ui" in item.keywords or "e2e" in item.keywords:
        item.add_marker(pytest.mark.xdist_group("browser"))


def _environment_file(env_name: str) -> Path:
    if not _ENV_NAME.fullmatch(env_name):
        raise pytest.UsageError("--env must be a name such as dev or qa, not a path.")
    if env_name == "dev":
        return _PROJECT_ROOT / ".env"
    return _PROJECT_ROOT / f".env.{env_name}"


def _load_environment(env_name: str) -> None:
    env_file = _environment_file(env_name)
    if not env_file.is_file():
        raise pytest.UsageError(
            f"--env {env_name} expects {env_file.name} in the project root. "
            "Copy .env.example and set the sandbox values."
        )
    load_dotenv(env_file)


def _required_env(name: str, env_name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"{name} is not set in {_environment_file(env_name).name} or the process environment."
        )
    return value


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """MyAccount origin from the environment file selected by --env."""
    return _required_env("BASE_URL", str(request.config.getoption("--env")))


@pytest.fixture(scope="session")
def payplus_client(request: pytest.FixtureRequest, base_url: str) -> PayPlusClient:
    """Authenticated PayPlus client for payment links and transactions."""
    env_name = str(request.config.getoption("--env"))
    api_url = os.getenv("API_BASE_URL", f"{base_url}/api")
    return PayPlusClient(
        base_url=api_url,
        api_key=_required_env("API_KEY", env_name),
        secret_key=_required_env("SECRET_KEY", env_name),
        payment_page_uid=_required_env("PAYMENT_PAGE_UID", env_name),
    )


@pytest.fixture
def driver(request: pytest.FixtureRequest) -> Iterator[WebDriver]:
    """
    Start Chrome through Selenium Manager, use a 1920x1080 viewport,
    and quit the browser when the test ends.
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

    driver_instance = webdriver.Chrome(options=options)

    yield driver_instance

    driver_instance.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[None],
) -> Iterator[None]:
    """Attach the URL, page source, and a screenshot when a browser test fails."""
    del call
    outcome = yield
    report = outcome.get_result()

    if report.failed and report.when in {"setup", "call"}:
        driver_instance = _driver_from_item(item)
        if driver_instance is not None:
            _attach_failure_artifacts(driver_instance)


def _driver_from_item(item: pytest.Item) -> WebDriver | None:
    funcargs = getattr(item, "funcargs", None) or {}
    driver_instance = funcargs.get("driver")
    if isinstance(driver_instance, WebDriver):
        return driver_instance
    page = funcargs.get("payment_page")
    driver_instance = getattr(page, "driver", None)
    if isinstance(driver_instance, WebDriver):
        return driver_instance
    return None


def _attach_failure_artifacts(driver: WebDriver) -> None:
    artifacts = (
        ("url_on_failure", lambda: driver.current_url, allure.attachment_type.TEXT),
        ("page_source_on_failure", lambda: driver.page_source, allure.attachment_type.HTML),
        ("screenshot_on_failure", driver.get_screenshot_as_png, allure.attachment_type.PNG),
    )
    for name, read, attachment_type in artifacts:
        try:
            allure.attach(read(), name=name, attachment_type=attachment_type)
        except Exception:
            logger.exception("Failed to attach %s to the Allure report", name)


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
