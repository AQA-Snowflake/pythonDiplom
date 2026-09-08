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

    def close(self):
        self.connection.close()