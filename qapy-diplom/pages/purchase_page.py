from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PurchasePage:
    def __init__(self, driver, base_url="http://localhost:8080"):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)

    """Для открытия страницы по умолчанию."""
    def open(self):
        self.driver.get(self.base_url)

    def click_buy_button(self):
        # Кнопка "Купить" (не "в кредит")
        buy_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
            '//button[contains(@class,"button_size_m") '
            'and not(contains(@class,"button_view_extra")) '
            'and normalize-space()="Купить"]'))
        )
        buy_btn.click()

    def click_credit_button(self):
        # Кнопка "Купить в кредит"
        credit_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
            '//button[contains(@class,"button_view_extra") '
            'and normalize-space()="Купить в кредит"]'))
        )
        credit_btn.click()

    def fill_card_fields(self, number, month, year, owner, cvc):
        # Используем ваши локаторы
        self.driver.find_element(By.XPATH, '//input[@placeholder="0000 0000 0000 0000"]').send_keys(number)
        self.driver.find_element(By.XPATH, '//input[@placeholder="08"]').send_keys(month)
        self.driver.find_element(By.XPATH, '//input[@placeholder="22"]').send_keys(year)
        # Поле "Владелец"
        self.driver.find_element(By.XPATH, '//span[contains(@class,"input__top") and text()="Владелец"]/following-sibling::span[@class="input__box"]/input').send_keys(owner)
        self.driver.find_element(By.XPATH, '//input[@placeholder="999"]').send_keys(cvc)

    """Отправка формы"""
    def submit_form(self):
        # ищем кнопку по тексту "Продолжить"
        submit_btn = WebDriverWait(self.driver, 17).until(
            EC.element_to_be_clickable((By.XPATH,
            '//button[text()="Продолжить"]'))
        )
        submit_btn.click()

    def get_notification_text(self):
        try:
            # Ищем уведомление по классам
            notification = WebDriverWait(self.driver, 8).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR,
                    ".notification_notification_status_ok, .notification_notification_status_error"))
            )
            return notification.text
        except:
            # если не нашли - возвращаем ответ ошибки
            return "No notification found"

    def has_field_errors(self):
        """Проверим, есть ли на странице элементы с классом ошибки."""
        errors = self.driver.find_elements(By.CSS_SELECTOR, ".input__sub.input__sub_error")
        return len(errors) > 0

    def is_credit_page_opened(self):
        return "credit" in self.driver.current_url.lower() or "кредит" in self.driver.page_source

    def is_form_submitted(self):
        """Проверим, появилось ли уведомление (успех/ошибка) после отправки."""
        try:
            self.wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR,
                    ".notification_notification_status_ok, .notification_notification_status_error"))
            )
            return True
        except:
            return False

    def check_price_info_displayed(self):
        """Проверим наличие информации о цене, милях и проценте."""
        try:
            self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'33 360 миль')]")))
            self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'До 7%')]")))
            self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'45 000 руб.')]")))
            return True
        except:
            return False

    def get_owner_value(self):
        try:
            field = self.driver.find_element(By.XPATH,
                                             '//span[contains(@class,"input__top") and text()="Владелец"]/following-sibling::span[@class="input__box"]/input')
            return field.get_attribute("value")
        except:
            return ""

    def get_field_value(self, placeholder):
        """Возвращает значение поля по плейсхолдеру."""
        try:
            field = self.driver.find_element(By.XPATH, f'//input[@placeholder="{placeholder}"]')
            return field.get_attribute("value")
        except:
            return ""

    def get_field_error(self, field_name):
        try:
            error = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH,
                                                  f'//span[contains(@class,"input__top") and text()="{field_name}"]/following-sibling::span[@class="input__sub"]'))
            )
            return error.text
        except:
            return ""

    # def get_field_error(self, field_name):
    #     """Возвращает текст ошибки для поля по его названию (видимому label)."""
    #     try:
    #         # Ищем элемент ошибки, связанный с полем
    #         error = self.driver.find_element(By.XPATH,
    #                                          f'//span[contains(@class,"input__top") and text()="{field_name}"]/following-sibling::span[@class="input__sub"]')
    #         return error.text
    #     except:
    #         return ""
