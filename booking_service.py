from datetime import datetime
from uuid import uuid4

from database import get_connection
from reservation_service import init_reservation_tables


def create_reservation(
    equipment_ids: list[str],
    start_time: str,
    end_time: str,
) -> dict:
    """为演示用户创建预约，多件器材必须全部可借。"""
    equipment_ids = [
        item.strip().upper() for item in equipment_ids
    ]

    if not equipment_ids or any(not item for item in equipment_ids):
        raise ValueError("请输入至少一个器材编号。")

    if len(equipment_ids) != len(set(equipment_ids)):
        raise ValueError("同一张预约单不能重复填写相同器材。")

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

    reservation_id = "R" + uuid4().hex
    equipment_names = []

    with get_connection() as connection:
        # 在同一个事务里检查并保存。
        # 防止两个预约同时检查通过，又同时写入。
        connection.execute("BEGIN IMMEDIATE")

        for equipment_id in equipment_ids:
            equipment = connection.execute(
                "SELECT name FROM equipment WHERE id = ?",
                (equipment_id,),
            ).fetchone()

            if equipment is None:
                raise ValueError(f"没有找到器材：{equipment_id}")

            conflict = connection.execute("""
                SELECT 1
                FROM reservations AS r
                JOIN reservation_items AS i
                    ON r.id = i.reservation_id
                WHERE i.equipment_id = ?
                  AND r.status = 'active'
                  AND r.start_time < ?
                  AND r.end_time > ?
                LIMIT 1
            """, (equipment_id, end_time, start_time)).fetchone()

            if conflict is not None:
                raise ValueError(
                    f"{equipment['name']} 在该时间段已有预约，"
                    "整单未创建。"
                )

            equipment_names.append(equipment["name"])

        # 所有器材检查通过后，写入预约单。
        connection.execute("""
            INSERT INTO reservations (
                id, user_id, start_time, end_time, status
            )
            VALUES (?, ?, ?, ?, 'active')
        """, (
            reservation_id,
            "demo-user",
            start_time,
            end_time,
        ))

        # 写入这张预约单包含的器材。
        connection.executemany("""
            INSERT INTO reservation_items (
                reservation_id, equipment_id
            )
            VALUES (?, ?)
        """, [
            (reservation_id, equipment_id)
            for equipment_id in equipment_ids
        ])

    # 离开上面的 with 后，数据才完成提交。
    return {
        "reservation_id": reservation_id,
        "equipment_names": equipment_names,
        "start_time": start_time,
        "end_time": end_time,
        "status": "active",
    }


if __name__ == "__main__":
    init_reservation_tables()

    raw_ids = input("器材编号（多件用英文逗号分隔）：")
    start_time = input("开始时间（格式：2026-10-13 14:00）：")
    end_time = input("结束时间（格式：2026-10-13 16:00）：")

    print(f"\n准备预约：{raw_ids}")
    print(f"时间：{start_time} 至 {end_time}")
    confirmation = input("确定创建预约吗？输入 y 确认：")

    if confirmation.strip().lower() != "y":
        print("已放弃操作，没有创建预约。")
    else:
        try:
            result = create_reservation(
                raw_ids.split(","),
                start_time,
                end_time,
            )

            print("\n预约成功！")
            print(f"预约编号：{result['reservation_id']}")
            print(f"器材：{'、'.join(result['equipment_names'])}")
            print(f"开始时间：{result['start_time']}")
            print(f"结束时间：{result['end_time']}")
        except ValueError as error:
            print(f"\n预约失败：{error}")