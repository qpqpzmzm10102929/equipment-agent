from database import get_connection
from reservation_service import init_reservation_tables


def list_reservations() -> list[dict]:
    """查询演示用户的全部预约，包括已取消的预约。"""
    results = []

    with get_connection() as connection:
        reservations = connection.execute("""
            SELECT
                id AS reservation_id,
                start_time,
                end_time,
                status
            FROM reservations
            WHERE user_id = ?
            ORDER BY start_time DESC, id
        """, ("demo-user",)).fetchall()

        for reservation in reservations:
            # 根据预约编号，查出这张预约单包含的器材。
            equipment = connection.execute("""
                SELECT
                    e.id AS equipment_id,
                    e.name
                FROM reservation_items AS i
                JOIN equipment AS e
                    ON i.equipment_id = e.id
                WHERE i.reservation_id = ?
                ORDER BY e.id
            """, (reservation["reservation_id"],)).fetchall()

            record = dict(reservation)
            record["equipment"] = [
                dict(item) for item in equipment
            ]
            results.append(record)

    return results


if __name__ == "__main__":
    init_reservation_tables()
    reservations = list_reservations()

    status_names = {
        "active": "有效",
        "cancelled": "已取消",
    }

    if not reservations:
        print("你目前没有预约记录。")
    else:
        print(f"共找到 {len(reservations)} 张预约单：\n")

        for reservation in reservations:
            names = [
                item["name"]
                for item in reservation["equipment"]
            ]

            print(f"预约编号：{reservation['reservation_id']}")
            print(f"器材：{'、'.join(names)}")
            print(f"开始时间：{reservation['start_time']}")
            print(f"结束时间：{reservation['end_time']}")
            print(f"状态：{status_names[reservation['status']]}")
            print("-" * 40)