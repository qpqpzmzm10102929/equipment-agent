from datetime import datetime

from database import get_connection


def check_availability(
    equipment_id: str,
    start_time: str,
    end_time: str,
) -> dict:
    """检查一件器材在指定时间段是否可借，时间统一按北京时间填写。"""

    # 先检查时间格式，并转换成统一格式，便于数据库比较。
    time_format = "%Y-%m-%d %H:%M"

    try:
        start = datetime.strptime(start_time.strip(), time_format)
        end = datetime.strptime(end_time.strip(), time_format)
    except ValueError:
        raise ValueError("时间格式应为：2026-10-13 14:00") from None

    if start >= end:
        raise ValueError("结束时间必须晚于开始时间。")

    start_time = start.strftime(time_format)
    end_time = end.strftime(time_format)
    equipment_id = equipment_id.strip().upper()

    with get_connection() as connection:
        equipment = connection.execute(
            "SELECT id, name FROM equipment WHERE id = ?",
            (equipment_id,),
        ).fetchone()

        if equipment is None:
            raise ValueError(f"没有找到器材：{equipment_id}")

        # 只检查有效预约，已取消的预约不会占用器材。
        conflicts = connection.execute("""
            SELECT r.start_time, r.end_time
            FROM reservations AS r
            JOIN reservation_items AS i
                ON r.id = i.reservation_id
            WHERE i.equipment_id = ?
              AND r.status = 'active'
              AND r.start_time < ?
              AND r.end_time > ?
            ORDER BY r.start_time
        """, (equipment_id, end_time, start_time)).fetchall()

    return {
        "equipment_id": equipment_id,
        "name": equipment["name"],
        "start_time": start_time,
        "end_time": end_time,
        "available": len(conflicts) == 0,
        "conflicts": [dict(row) for row in conflicts],
    }


if __name__ == "__main__":
    from reservation_service import init_reservation_tables

    init_reservation_tables()

    equipment_id = input("请输入器材编号，例如 EQ003：")
    start_time = input("开始时间（格式：2026-10-13 14:00）：")
    end_time = input("结束时间（格式：2026-10-13 16:00）：")

    try:
        result = check_availability(
            equipment_id, start_time, end_time
        )

        print(f"\n器材：{result['name']}")

        if result["available"]:
            print("查询结果：该时间段可以借用。")
        else:
            print("查询结果：该时间段已有预约，无法借用。")
            for conflict in result["conflicts"]:
                print(
                    f"占用时间：{conflict['start_time']}"
                    f" 至 {conflict['end_time']}"
                )
    except ValueError as error:
        print(f"输入有误：{error}")