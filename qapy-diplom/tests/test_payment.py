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
from datetime import datetime
from pages.purchase_page import PurchasePage
from db.db_client import DBClient

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

@pytest.mark.usefixtures("driver")
class TestPayment:
    """
    Класс с тестами формы оплаты.
    Фикстура driver (см. conftest.py) создаёт браузер на каждый тест и
    закрывает после.
    """

    # P001: Проверка успешного платежа дебетовой картой с проверкой уведомлений в БД
    def test_successful_debit_payment(self, driver):
        """
        Проверяем полный happy path:
        1. Открываем страницу и жмём "Купить".
        2. Заполняем форму валидными данными с APPROVED-картой.
        3. Отправляем форму.
        4. Ждём уведомление об успехе на UI.
        5. Проверяем, что в БД последний платёж имеет статус APPROVED.
        """
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        # Валидный номер карты (approved) из data.json
        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()

        # Проверяем уведомление
        notification = page.get_notification_text()
        assert "Успешно" in notification or "Approved" in notification, \
            f"Ожидалось уведомление об успехе, получили: {notification!r}"

        # Проверяем БД: последний платёж должен быть APPROVED
        with DBClient() as db:
            last_payment = db.wait_for_last_payment(timeout=10)
            assert last_payment is not None, "В БД не появилась запись о платеже"
            assert last_payment["status"] == "APPROVED", \
                f"Ожидался статус APPROVED, получили {last_payment['status']!r}"

    # P002: Валидация номера карты
    def test_valid_card_number_format(self, driver):
        """Корректный 16-значный номер не вызывает ошибок валидации."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "123")
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном номере"
        value = page.get_field_value("0000 0000 0000 0000")
        assert len(value.replace(" ", "")) == 16, "Номер должен содержать 16 цифр"

    def test_invalid_card_number_too_short(self, driver):
        """Слишком короткий номер подсвечивается ошибкой 'Неверный формат'."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("123", "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error or "заполнено" in error, \
            f"Ожидалась ошибка формата, получили: {error!r}"

    def test_empty_card_number(self, driver):
        """Пустое поле номера карты — форма не отправляется, есть ошибка."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("", "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        assert not page.is_form_submitted(), "Форма отправилась, хотя поле пустое"
        error = page.get_field_error("Номер карты")
        assert "Неверный формат" in error

    # P003: Валидация месяца, года
    def test_valid_month(self, driver):
        """Корректный месяц (09) проходит валидацию."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields(CARD_APPROVED, "09", future_year(), "Valeria Petrovna", "123")

        assert not page.has_field_errors(), "Есть ошибки валидации при корректном месяце"
        value = page.get_field_value("08")
        assert value == "09"

    def test_invalid_month_13(self, driver):
        """Месяц 13 не существует — должна быть ошибка."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "13", future_year(), "Valeria Petrovna", "123")
        page.submit_form()
        error = page.get_field_error("Месяц")
        assert "Неверно указан срок" in error or "срок действия" in error, \
            f"Ожидалась ошибка месяца, получили: {error!r}"

    def test_expired_card_year(self, driver):
        """
        Проверяем, что карта с прошедшим годом не проходит валидацию.
        Ожидаем ошибку 'Истёк срок действия карты'
        (или похожую) под полем 'Год'.
        """
        page = PurchasePage(driver)
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
    def test_valid_owner(self, driver):
        """Латиница в поле 'Владелец' сохраняется без ошибок."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        page.fill_card_fields("4444 4444 4444 4441", "12", future_year(), "Valeria Petrovna", "123")
        # Проверяем, что введённое значение реально сохранилось в поле
        assert not page.has_field_errors(), "Есть ошибки валидации при корректном владельце"
        assert page.get_owner_value() == "Valeria Petrovna"


    @pytest.mark.xfail(reason="Баг: поле Владелец пропускает кириллицу")
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
    def test_valid_cvc(self, driver):
        """Корректный CVC из 3 цифр проходит валидацию."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()

        page.fill_card_fields(CARD_APPROVED, "12", future_year(), "Valeria Petrovna", "567")

        assert not page.has_field_errors(), "Есть ошибки валидации при корректных данных cvc"
        assert page.get_field_value("999") == "567"


    @pytest.mark.xfail(reason="Баг: валидация CVC не проверяет длину")
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
    def test_declined_debit_payment(self, driver):
        """Карта DECLINED - на UI ошибка, в БД статус DECLINED."""
        page = PurchasePage(driver)
        page.open()
        page.click_buy_button()
        # Номер карты из data.json со статусом declined (например, "4444 4444 4444 4442")
        page.fill_card_fields(CARD_DECLINED, "12", future_year(), "Valeria Petrovna", "123")
        page.submit_form()

        notification = page.get_notification_text()
        assert "Ошибка" in notification or "Declined" in notification, \
            f"Ожидалось уведомление об ошибке, получили: {notification!r}"
        # Проверка БД (опционально)
        with DBClient() as db:
            last_payment = db.wait_for_last_payment(timeout=10)
            assert last_payment is not None, "В БД не появилась запись о платеже"
            assert last_payment["status"] == "DECLINED", \
                f"Ожидался статус DECLINED, получили {last_payment['status']!r}"

    # P007: Кнопка "Купить в кредит"
    def test_credit_button(self, driver):
        """Нажатие на 'Купить в кредит' открывает страницу кредита."""
        page = PurchasePage(driver)
        page.open()
        page.click_credit_button()

        assert page.is_credit_page_opened(), "Страница кредита не открылась"

    # P008: Отображение цены, миль, процентов
    def test_price_info_displayed(self, driver):
        """На главной странице видны цена, мили и процент кешбэка."""
        page = PurchasePage(driver)
        page.open()

        assert page.check_price_info_displayed(), "Ценовая информация не отображается"