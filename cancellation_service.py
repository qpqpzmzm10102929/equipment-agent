from database import get_connection
from reservation_service import init_reservation_tables


def cancel_reservation(reservation_id: str) -> dict:
    """取消演示用户的指定预约，保留原始记录。"""
    reservation_id = reservation_id.strip()

    if not reservation_id:
        raise ValueError("预约编号不能为空。")

    with get_connection() as connection:
        # 将查询和状态修改放在同一个事务中。
        connection.execute("BEGIN IMMEDIATE")

        reservation = connection.execute("""
            SELECT status
            FROM reservations
            WHERE id = ? AND user_id = ?
        """, (reservation_id, "demo-user")).fetchone()

        if reservation is None:
            raise ValueError("没有找到属于你的这张预约单。")

        if reservation["status"] == "cancelled":
            message = "这张预约单已经取消，无需重复操作。"
        else:
            connection.execute("""
                UPDATE reservations
                SET status = 'cancelled'
                WHERE id = ? AND user_id = ?
            """, (reservation_id, "demo-user"))

            message = "预约已取消，器材对应时段已释放。"

    return {
        "reservation_id": reservation_id,
        "status": "cancelled",
        "message": message,
    }


if __name__ == "__main__":
    init_reservation_tables()

    reservation_id = input("请输入要取消的完整预约编号：")

    print(f"\n准备取消整张预约单：{reservation_id}")
    confirmation = input("确定取消吗？输入 y 确认：")

    if confirmation.strip().lower() != "y":
        print("已放弃操作，预约保持原样。")
    else:
        try:
            result = cancel_reservation(reservation_id)
            print(f"\n{result['message']}")
            print(f"预约编号：{result['reservation_id']}")
        except ValueError as error:
            print(f"\n取消失败：{error}")