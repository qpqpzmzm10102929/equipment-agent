import sqlite3
from contextlib import contextmanager
from pathlib import Path

from equipment_data import EQUIPMENT


# 数据库固定保存在项目的 data 文件夹中。
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "equipment.db"


@contextmanager
def get_connection():
    """打开数据库，操作成功后提交，出错时回滚，最后关闭连接。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_database():
    """创建器材表，并导入初始器材数据。"""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        # 编号已存在时跳过，重复运行不会重复添加器材。
        connection.executemany("""
            INSERT INTO equipment (id, name, category, description)
            VALUES (:id, :name, :category, :description)
            ON CONFLICT(id) DO NOTHING
        """, EQUIPMENT)


if __name__ == "__main__":
    init_database()

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM equipment ORDER BY id"
        ).fetchall()

    print(f"数据库初始化成功：{DB_PATH}")
    print(f"数据库中共有 {len(rows)} 件器材：\n")

    for row in rows:
        print(f"{row['id']} | {row['name']} | {row['category']}")