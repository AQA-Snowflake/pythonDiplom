import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pages.purchase_page import PurchasePage
from db.db_client import DBClient
import time

@pytest.mark.usefixtures("driver")
class TestPayment:

        # P001: Проверка успешного платежа с проверкой уведомлений в БД
    def test_successful_debit_payment(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        # Валидный номер карты (approved) из data.json
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Valeria Petrovna", "123")
        page.submit_form()

        # Проверяем уведомление
        notification = page.get_notification_text()
        assert "Успешно" in notification or "Approved" in notification

        # Проверяем БД: последний платёж должен быть APPROVED
        db = DBClient()
        time.sleep(1)  # небольшая задержка для записи в БД
        last_payment = db.get_last_payment()
        assert last_payment is not None
        assert last_payment['status'] == 'APPROVED'
        db.close()

        # P002: Валидация номера карты
    def test_valid_card_number_format(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Valeria Petrovna", "123")
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном номере"
        value = page.get_field_value("0000 0000 0000 0000")
        assert len(value.replace(" ", "")) == 16, "Номер должен содержать 16 цифр"

    def test_invalid_card_number_too_short(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("123", "12", "25", "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error or "заполнено" in error

        # P003: Валидация месяца
    def test_valid_month(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "09", "25", "Valeria Petrovna", "123")
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном месяце"
        value = page.get_field_value("08")
        assert value == "09"

    def test_invalid_month_13(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "13", "25", "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Месяц")
        assert "Неверно указан срок" in error or "срок действия" in error

        # P004: Валидация владельца
    def test_valid_owner(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Valeria Petrovna", "123")
        # Владелец заполняется через сложный локатор, но проверим значение через get_field_value по плейсхолдеру "Иванов Иван"
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном месяце"
        value = page.get_owner_value()
        assert value == "Valeria Petrovna"

    @pytest.mark.xfail(reason="Баг: поле Владелец пропускает кириллицу")
    def test_invalid_owner_cyrillic(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Валерия Петровна", "123")
        page.submit_form()
        error = page.get_field_error("Владелец")
        assert "латинские" in error or "неверный" in error

        # P005: Валидация CVC
    def test_valid_cvc(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Valeria Petrovna", "567")
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном месяце"
        value = page.get_field_value("999")
        assert value == "567"


    @pytest.mark.xfail(reason="Баг: валидация CVC не проверяет длину")
    # декоратор
    def test_invalid_cvc_too_short(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", "25", "Valeria Petrovna", "12")
        page.submit_form()
        error = page.get_field_error("CVC")
        assert "заполнено" in error or "3 цифры" in error

        # P006:
    def test_declined_debit_payment(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        # Номер карты из data.json со статусом declined (например, "4444 4444 4444 4442")
        page.fill_card_fields("4444 4444 4444 4442", "12", "25", "Valeria Petrovna", "123")
        page.submit_form()

        notification = page.get_notification_text()
        assert "Ошибка" in notification or "Declined" in notification
        # Проверка БД (опционально)
        db = DBClient()
        time.sleep(1)
        last_payment = db.get_last_payment()
        assert last_payment is not None
        assert last_payment['status'] == 'DECLINED'
        db.close()

        # P007: Отправка с пустым обязательным полем
    def test_empty_card_number(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("", "12", "25", "Valeria Petrovna", "123")
        page.submit_form()
        assert not page.is_form_submitted(), "Форма отправилась, хотя поле пустое"
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error

        # P008: Кнопка "Купить в кредит"
    def test_credit_button(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_credit_button()
        assert page.is_credit_page_opened(), "Страница кредита не открылась"

        # P009: Отображение цены, миль, процентов
    def test_price_info_displayed(self, driver):
        page = PurchasePage(driver)
        page.open()
        assert page.check_price_info_displayed(), "Ценовая информация не отображается"