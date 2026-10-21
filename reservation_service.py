from database import get_connection, init_database


def init_reservation_tables():
    """创建预约表和预约明细表。"""
    # 确保器材表已存在。
    init_database()

    with get_connection() as connection:
        # 一条记录代表一张预约单。
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'cancelled')),
                CHECK (start_time < end_time)
            )
        """)

        # 一张预约单可以关联多件器材。
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reservation_items (
                reservation_id TEXT NOT NULL,
                equipment_id TEXT NOT NULL,

                PRIMARY KEY (reservation_id, equipment_id),

                FOREIGN KEY (reservation_id)
                    REFERENCES reservations(id),

                FOREIGN KEY (equipment_id)
                    REFERENCES equipment(id)
            )
        """)


if __name__ == "__main__":
    init_reservation_tables()

    with get_connection() as connection:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN (
                  'equipment',
                  'reservations',
                  'reservation_items'
              )
            ORDER BY name
        """).fetchall()

    print("数据库表准备完成：")

    for table in tables:
        print(f"- {table['name']}")