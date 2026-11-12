from __future__ import annotations

from typing import Any

import allure
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_SET_CONTROL_VALUE = """
const element = arguments[0];
const value = arguments[1];
const descriptor = Object.getOwnPropertyDescriptor(
  Object.getPrototypeOf(element),
  "value"
);
descriptor.set.call(element, value);
element.dispatchEvent(new Event("input", { bubbles: true }));
element.dispatchEvent(new Event("change", { bubbles: true }));
"""


class BasePage:
    def __init__(self, driver: WebDriver, timeout: int = 10) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    @allure.step("Open URL: {url}")
    def open(self, url: str) -> None:
        self.driver.get(url)

    @allure.step("Click element: {locator}")
    def click(self, locator: tuple[str, str], *, timeout: int | None = None) -> None:
        element = self._until(EC.element_to_be_clickable(locator), timeout)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            element,
        )
        element.click()

    @allure.step("Type text into element: {locator}")
    def type_text(self, locator: tuple[str, str], text: str) -> None:
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.clear()
        element.send_keys(text)
        self._dispatch_input(element)

    @allure.step("Select {value} in element: {locator}")
    def select_by_value(self, locator: tuple[str, str], value: str) -> None:
        """Set a select value and notify Vue.

        Clicking the native option updates the DOM but leaves the PayPlus
        Vue model empty, so expiry validation still says the field is
        required. Setting the value through the DOM property and dispatching
        input/change updates the model the submit handler actually reads.
        """
        element = self.wait.until(EC.presence_of_element_located(locator))
        self.driver.execute_script(_SET_CONTROL_VALUE, element, value)

    @allure.step("Read the current URL")
    def current_url(self) -> str:
        return self.driver.current_url

    def _until(self, condition: Any, timeout: int | None = None) -> Any:
        wait = self.wait if timeout is None else WebDriverWait(self.driver, timeout)
        return wait.until(condition)

    def _dispatch_input(self, element: WebElement) -> None:
        self.driver.execute_script(
            """
            arguments[0].dispatchEvent(new Event("input", { bubbles: true }));
            arguments[0].dispatchEvent(new Event("change", { bubbles: true }));
            """,
            element,
        )
