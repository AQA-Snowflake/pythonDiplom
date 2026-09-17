import time
import pymysql

class DBClient:
    def __init__(self, host='localhost', port=3307, user='app', password='pass', db='app'):
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            cursorclass=pymysql.cursors.DictCursor
        )

    def get_payment_status(self, payment_id):
        # Пример: получить статус платежа по ID
        with self.connection.cursor() as cursor:
            sql = "SELECT status FROM payment_entity WHERE id = %s"
            cursor.execute(sql, (payment_id,))
            result = cursor.fetchone()
            return result['status'] if result else None

    def get_last_payment(self):
        # Получить последнюю запись из payment_entity
        with self.connection.cursor() as cursor:
            sql = "SELECT * FROM payment_entity ORDER BY created DESC LIMIT 1"
            cursor.execute(sql)
            return cursor.fetchone()

    def wait_for_last_payment(self, timeout: int = 10, poll_interval: float = 0.5):
        """
        Ждёт появления записи в debit - payment_entity (дебетовые операции).
        Для кредитов используйте wait_for_last_credit / wait_for_last_operation.
        Возвращает последнюю запись или None, если за timeout ничего не появилось.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            row = self.get_last_payment()
            if row is not None:
                return row
            time.sleep(poll_interval)
        return None

    def get_last_credit(self):
        """Последняя запись из credit_request_entity (отдельная таблица для кредитов)."""
        with self.connection.cursor() as cursor:
            sql = "SELECT * FROM credit_request_entity ORDER BY created DESC LIMIT 1"
            cursor.execute(sql)
            return cursor.fetchone()

    def wait_for_last_credit(self, timeout: int = 10, poll_interval: float = 0.5):
        """Ждёт появления записи в credit_request_entity (аналог wait_for_last_payment)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            row = self.get_last_credit()
            if row is not None:
                return row
            time.sleep(poll_interval)
        return None

    def wait_for_last_operation(self, pay_type: str, timeout: int = 10):
        """
        Универсальная точка входа: тест говорит только 'debit' или 'credit',
        а клиент сам выбирает нужную таблицу.
        """
        if pay_type == "credit":
            return self.wait_for_last_credit(timeout=timeout)
        return self.wait_for_last_payment(timeout=timeout)

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    # Позволяет использовать `with DBClient() as db:` и автоматически закрывать соединение
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()