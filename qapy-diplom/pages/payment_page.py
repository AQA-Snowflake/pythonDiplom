from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PaymentPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def fill_card_data(self, number, month, year, owner, cvc):
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']").send_keys(number)
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='08']").send_keys(month)
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='22']").send_keys(year)
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Иванов Иван']").send_keys(owner)
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='999']").send_keys(cvc)

    def submit(self):
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def get_success_message(self):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".notification_status_ok"))).text

    def get_error_message(self):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".notification_status_error"))).text