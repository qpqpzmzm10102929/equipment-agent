from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from equipment_service import search_equipment as search_impl
from availability_service import check_availability as availability_impl
from booking_service import create_reservation as booking_impl
from my_reservations import list_reservations as list_impl
from cancellation_service import cancel_reservation as cancel_impl
from reservation_service import init_reservation_tables


mcp = MCPServer(
    "equipment-agent",
    instructions=(
        "这是校园器材借用服务，当前用户固定为 demo-user。"
        "时间均使用北京时间，格式为 YYYY-MM-DD HH:MM。"
        "创建预约前，应向用户说明器材和时间并获得确认。"
        "取消预约前，应明确要取消的预约单并获得确认。"
        "必须根据工具的实际返回结果说明操作是否成功。"
    ),
)


@mcp.tool()
def search_equipment(keyword: str = "") -> list[dict]:
    """按关键词查询器材的编号、名称、类别和说明。留空返回全部器材。"""
    return search_impl(keyword)


@mcp.tool()
def check_availability(
    equipment_id: str,
    start_time: str,
    end_time: str,
) -> dict:
    """检查一件器材是否可借。时间格式为 YYYY-MM-DD HH:MM，北京时间。"""
    try:
        return availability_impl(
            equipment_id, start_time, end_time
        )
    except ValueError as error:
        raise ToolError(str(error)) from error


@mcp.tool()
def create_reservation(
    equipment_ids: list[str],
    start_time: str,
    end_time: str,
) -> dict:
    """用户确认器材和时间后创建预约。多件器材必须全部可借才整单成功。"""
    try:
        return booking_impl(
            equipment_ids, start_time, end_time
        )
    except ValueError as error:
        raise ToolError(str(error)) from error


@mcp.tool()
def list_reservations() -> list[dict]:
    """查询当前演示用户的全部预约，包含器材、时间、状态和预约编号。"""
    return list_impl()


@mcp.tool()
def cancel_reservation(reservation_id: str) -> dict:
    """用户明确确认后，按完整预约编号取消整张预约单，释放全部器材。"""
    try:
        return cancel_impl(reservation_id)
    except ValueError as error:
        raise ToolError(str(error)) from error


if __name__ == "__main__":
    init_reservation_tables()
    mcp.run(transport="stdio")