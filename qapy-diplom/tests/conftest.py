import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

IS_CI = bool(os.getenv("CI"))


@pytest.fixture(scope="function")
def driver():
    options = Options()
    if IS_CI:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "profile.default_content_setting_values.notifications": 2,
        })
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
    else:
        options.add_argument("--start-maximized")

    mac_chromedriver = "/usr/local/bin/chromedriver"
    if not IS_CI and Path(mac_chromedriver).exists():
        service = Service(mac_chromedriver)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # В CI chromedriver будет в PATH, установлен шагом setup-chromedriver
        driver = webdriver.Chrome(options=options)

    if not IS_CI:
        driver.maximize_window()

    yield driver
    driver.quit()

@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:8080"