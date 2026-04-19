import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()


class DataBase:
    _instance = None

    # ── conexión ─────────────────────────────────────────────────────────────

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        self._conn = pymysql.connect(
            host        = os.environ["DB_HOST"],
            port        = int(os.environ["DB_PORT"]),
            user        = os.environ["DB_USER"],
            password    = os.environ["DB_PASSWORD"],
            database    = os.environ["DB_NAME"],
            ssl         = {"ssl_disabled": False},
            autocommit  = True,
            cursorclass = pymysql.cursors.DictCursor,
        )

    def _cursor(self):
        """Reconecta si la conexión se cayó."""
        try:
            self._conn.ping(reconnect=True)
        except Exception:
            self._connect()
        return self._conn.cursor()

    # ── query genérica ────────────────────────────────────────────────────────

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Ejecuta cualquier SQL.
        Normaliza placeholders: acepta ? (sqlite-style) y %s (pymysql-style).
        - SELECT  → devuelve list[dict]
        - INSERT  → devuelve [{"lastrowid": id}]
        - UPDATE/DELETE → devuelve [{"rowcount": n}]
        """
        cur = self._cursor()
        try:
            cur.execute(sql.replace("?", "%s"), params)
            verb = sql.strip().split()[0].upper()
            if verb == "SELECT":
                return cur.fetchall()
            elif verb == "INSERT":
                return [{"lastrowid": cur.lastrowid}]
            else:
                return [{"rowcount": cur.rowcount}]
        finally:
            cur.close()

    # ── setup ─────────────────────────────────────────────────────────────────

    def create_table(self):
        self.query("""
            CREATE TABLE IF NOT EXISTS products (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                name        VARCHAR(255)    NOT NULL,
                description TEXT,
                price       DECIMAL(10, 2)  DEFAULT 0.00,
                badge       VARCHAR(50)     DEFAULT '',
                stock       INT             DEFAULT 0,
                image       VARCHAR(500)    DEFAULT ''
            )
        """)

    # ── productos ─────────────────────────────────────────────────────────────

    def get_recent_products(self, limit: int = 5) -> list[dict]:
        return self.query(
            "SELECT id, name, description, price, image, badge "
            "FROM products ORDER BY id DESC LIMIT %s",
            (limit,)
        )

    def get_all_products(self) -> list[dict]:
        return self.query(
            "SELECT id, name, description, price, image, badge "
            "FROM products ORDER BY id DESC"
        )

    def get_all_products_admin(self) -> list[dict]:
        return self.query(
            "SELECT id, name, description, price, image, badge, stock "
            "FROM products ORDER BY id DESC"
        )

    def get_product_image(self, product_id: int) -> list[dict]:
        return self.query(
            "SELECT image FROM products WHERE id = %s",
            (product_id,)
        )

    def create_product(self, name, description, price, badge, stock, image) -> list[dict]:
        return self.query(
            "INSERT INTO products (name, description, price, badge, stock, image) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, description, price, badge, stock, image)
        )

    def update_product(self, product_id, name, description, price, badge, stock, image) -> list[dict]:
        return self.query(
            "UPDATE products "
            "SET name=%s, description=%s, price=%s, badge=%s, stock=%s, image=%s "
            "WHERE id=%s",
            (name, description, price, badge, stock, image, product_id)
        )

    def delete_product(self, product_id: int) -> list[dict]:
        return self.query(
            "DELETE FROM products WHERE id = %s",
            (product_id,)
        )


# singleton global
database = DataBase()
database.create_table()