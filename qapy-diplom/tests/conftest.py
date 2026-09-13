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