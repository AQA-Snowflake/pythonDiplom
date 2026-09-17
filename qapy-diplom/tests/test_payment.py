"""
Тесты для формы оплаты на сайте "Путешествие дня".

Проверяем:
  - Успешную и неуспешную оплату дебетовой картой (с проверкой БД)
  - Валидацию полей формы: номер карты, месяц, год, владелец, CVC
  - Переключение между вкладками "Купить" и "Купить в кредит"
  - Отображение информации о цене/милях/процентах на странице

Тестовые карты (из data.json gate-simulator):
  - 4444 4444 4444 4441 → APPROVED (успешная оплата)
  - 4444 4444 4444 4442 → DECLINED (банк отказывает)
"""

import pytest
import allure
from datetime import datetime
from pages.purchase_page import PurchasePage
from db.db_client import DBClient
pytestmark = [allure.suite("Тесты оплаты")]

# Вспомогательные функции

def future_year(years_ahead: int = 4) -> str:
    """
    Возвращает год в формате 'YY', который гарантированно в будущем.
    Нужно, чтобы карта не считалась просроченной (иначе форма не отправится).

    Пример: если сейчас 2026 год и years_ahead=4, вернёт '30'.
    """
    return str((datetime.now().year + years_ahead) % 100).zfill(2)

# Значения карт для тестов
CARD_APPROVED = "4444 4444 4444 4441"   # успешная оплата
CARD_DECLINED = "4444 4444 4444 4442"   # банк отклоняет

@allure.epic("Путешествие дня")
@allure.feature("Форма оплаты")
@pytest.mark.usefixtures("driver")
class TestPayment:
    """
    Класс с тестами формы оплаты.
    Фикстура driver (см. conftest.py) создаёт браузер на каждый тест и
    закрывает после.
    """

    # P001: Проверка успешного платежа дебетовой картой+кредитной картой с проверкой уведомлений в БД
    @pytest.mark.parametrize("pay_type", ["debit", "credit"])
    @allure.title("Успешная оплата ({pay_type})")
    @allure.description("Проверяет happy path для debit и credit: заполнение формы, отправка, "
        "успешное уведомление на UI и статус APPROVED в соответствующей таблице БД."
    )
    def test_successful_debit_payment(self, driver, base_url, pay_type):
        page = PurchasePage(driver, base_url=base_url)
        page.open()
        # Выбор вкладки
        page.select_payment_type(pay_type)
        # Валидный номер карты (approved) из data.json
        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()

        # Проверяем уведомление
        notification = page.wait_for_success_notification(timeout=10)
        assert "Успешно" in notification, \
            f"Ожидалось уведомление об успехе, получили: {notification!r}"
        assert "Операция одобрена Банком" in notification, \
            f"Ожидалось 'Операция одобрена Банком', получили: {notification!r}"

        # Проверяем БД
        with DBClient() as db:
            last = db.wait_for_last_operation(pay_type, timeout=10)
            assert last is not None, "В БД не появилась запись о платеже"
            assert last["status"] == "APPROVED", \
                f"Ожидался статус APPROVED, получили {last['status']!r}"

    # P002: Валидация номера карты
    @allure.title("Валидация: Корректный формат номера карты 16-значный")
    def test_valid_card_number_format(self, driver, base_url):
        page = PurchasePage(driver, base_url=base_url)
        page.open()
        page.click_buy_button()
        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "123")
        # Проверяем отсутствие ошибки именно под полем «Номер карты»
        error = page.get_field_error("Номер карты")
        assert error == "", f"Ожидалось отсутствие ошибки, получили: {error!r}"
        value = page.get_field_value("0000 0000 0000 0000")
        assert len(value.replace(" ", "")) == 16, "Номер должен содержать 16 цифр"

    @allure.title("Валидация: Слишком короткий номер карты")
    def test_invalid_card_number_too_short(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("123", "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error or "заполнено" in error, \
            f"Ожидалась ошибка формата, получили: {error!r}"

    @pytest.mark.parametrize("pay_type", ["debit", "credit"])
    @allure.title("Валидация: Пустое поле номера карты ({pay_type})")
    def test_empty_card_number(self, driver, base_url, pay_type):
        page = PurchasePage(driver, base_url=base_url)
        page.open()
        page.select_payment_type(pay_type)
        page.fill_card_fields("", "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        assert not page.is_form_submitted(), \
            f"[{pay_type}] Форма отправилась, хотя поле пустое"
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error, \
                f"[{pay_type}] Ожидалась ошибка формата, получили: {error!r}"

    # P003: Валидация месяца, года
    @allure.title("Валидация: Корректный месяц (09)")
    def test_valid_month(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields(CARD_APPROVED, "09", future_year(), "Valeria Petrovna", "123")

        assert not page.has_field_errors(), "Есть ошибки валидации при корректном месяце"
        value = page.get_field_value("08")
        assert value == "09"

    @allure.title("Валидация: Несуществующий месяц (13)")
    def test_invalid_month_13(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "13", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Месяц")
        assert "Неверно указан срок" in error or "срок действия" in error, \
            f"Ожидалась ошибка месяца, получили: {error!r}"

    @allure.title("Валидация: Просроченный год карты")
    def test_expired_card_year(self, driver, base_url):
        """ Ожидаем ошибку 'Истёк срок действия карты' (или похожую) """
        page = PurchasePage(driver, base_url=base_url)
        page.open()
        page.click_buy_button()
        # Год на 1 меньше текущего (то есть, просрочен точно)
        past_year = str((datetime.now().year - 1) % 100).zfill(2)
        page.fill_card_fields(CARD_APPROVED, "12", past_year, "Valeria Petrovna", "123")
        page.submit_form()

        error = page.get_field_error("Год")
        assert "истёк" in error.lower() or "срок действия" in error.lower(), \
            f"Ожидалась ошибка о просроченной карте, получили: {error!r}"
        # Форма не должна отправиться
        assert not page.is_form_submitted(), "Форма отправилась с просроченной картой"

    # P004: Валидация владельца
    @allure.title("Валидация: Корректный владелец (латиница)")
    def test_valid_owner(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", future_year(), "Valeria Petrovna", "123")
        # Проверяем, что введённое значение реально сохранилось в поле
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном владельце"
        assert page.get_owner_value() == "Valeria Petrovna"

    @allure.title("Поле 'Владелец' пропускает кириллицу")
    @pytest.mark.xfail(reason="поле Владелец пропускает кириллицу")
    def test_invalid_owner_cyrillic(self, driver):
        """Кириллица в поле 'Владелец' должна отклоняться — сейчас пропускается."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Валерия Петровна", "123")
        page.submit_form()
        error = page.get_field_error("Владелец")
        assert "латинские" in error or "неверный" in error

    # P005: Валидация CVC
    @allure.title("Валидация: Корректный CVC")
    def test_valid_cvc(self, driver):
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "567")

        assert not page.has_field_errors(), "Есть ошибки валидации при корректных данных cvc"
        assert page.get_field_value("999") == "567"


    @allure.title("Валидация CVC не проверяет длину")
    @pytest.mark.xfail(reason="валидация CVC не проверяет длину")
    # декоратор
    def test_invalid_cvc_too_short(self, driver):
        """CVC из 2 цифр должен отклоняться — сейчас пропускается."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "12")
        page.submit_form()
        error = page.get_field_error("CVC")
        assert "заполнено" in error or "3 цифры" in error

    # P006: Отклоненная оплата
    @pytest.mark.parametrize("pay_type", ["debit", "credit"])
    @pytest.mark.xfail(reason="declined-карта 4442 отображает успех вместо отказа")
    @allure.title("Отклоненная оплата ({pay_type})")
    @allure.description(
        "Карта 4444 4444 4444 4442 должна получать отказ банка, "
        "но UI показывает 'Успешно / Операция одобрена Банком'. "
        "Оформлено как xfail"
    )
    def test_declined_debit_payment(self, base_url, pay_type):
        """Карта DECLINED - на UI ошибка, в БД статус DECLINED."""
        page = PurchasePage(driver, base_url=base_url)
        page.open()
        page.select_payment_type(pay_type)
        # Номер карты из data.json со статусом declined (например, "4444 4444 4444 4442")
        page.fill_card_fields(CARD_DECLINED, "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()

        # Ждём именно error-уведомление (не ok!)
        notification = page.wait_for_error_notification(timeout=5)
        assert ("Ошибка" in notification
                or "Declined" in notification
                or "отклонен" in notification.lower()), \
            f"[{pay_type}] Ожидалось уведомление об ошибке, получили: {notification!r}"
        # Проверка БД (опционально)
        with DBClient() as db:
            last = db.wait_for_last_operation(timeout=10)
            assert last is not None, f"[{pay_type}] В БД не появилась запись о платеже"
            assert last["status"] == "DECLINED", \
                f"Ожидался статус DECLINED, получили {last['status']!r}"

    # P007: Кнопка "Купить в кредит"
    @allure.title("Переключение на вкладку 'Купить в кредит'")
    def test_credit_button(self, driver):
        """Нажатие на 'Купить в кредит' открывает страницу кредита."""
        page = PurchasePage(driver)
        page.open()
        page.click_credit_button()

        assert page.is_credit_page_opened(), "Страница кредита не открылась"

    # P008: Отображение цены, миль, процентов
    @allure.title("Отображение цены, миль и процентов кешбэка")
    def test_price_info_displayed(self, driver):
        page = PurchasePage(driver)
        page.open()

        assert page.check_price_info_displayed(), "Ценовая информация не отображается"