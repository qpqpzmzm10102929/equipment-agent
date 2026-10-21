import asyncio
import copy
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


BASE_DIR = Path(__file__).resolve().parent

# 只有这两种操作允许通过网页确认按钮执行。
WRITE_TOOLS = {
    "create_reservation",
    "cancel_reservation",
}


def unpack_result(result):
    """兼容 MCP 的结构化结果和文本 JSON 结果。"""
    texts = [
        block.text
        for block in result.content
        if block.type == "text"
    ]

    data = result.structured_content

    # 当前服务可能将业务结果放在文本中。
    if data is None and len(texts) == 1:
        try:
            data = json.loads(texts[0])
        except (ValueError, TypeError):
            pass

    return {
        "is_error": result.is_error,
        "data": data,
        "text": texts,
        "outcome_unknown": False,
    }


async def _execute_action(action):
    name = action["tool"]
    arguments = copy.deepcopy(action["arguments"])

    if name not in WRITE_TOOLS:
        raise ValueError("不支持的操作。")

    if not isinstance(arguments, dict):
        raise ValueError("操作参数必须是对象。")

    server = StdioServerParameters(
        command=sys.executable,
        args=[
            "-X",
            "utf8",
            str(BASE_DIR / "mcp_server.py"),
        ],
        cwd=str(BASE_DIR),
    )

    # 用于区分“尚未发起操作”和“操作结果不确定”。
    call_started = False
    payload = None

    try:
        async with Client(
            server,
            read_timeout_seconds=30,
        ) as client:
            call_started = True

            # 每次点击只发送一次操作，不自动重试。
            result = await client.call_tool(
                name,
                arguments,
            )
            payload = unpack_result(result)

    except Exception:
        # 已收到工具结果时，连接关闭异常不覆盖业务结果。
        if payload is None:
            if call_started:
                message = (
                    "未能取得确定的操作结果。"
                    "请先查询我的预约，确认是否已生效，"
                    "不要直接重复提交。"
                )
            else:
                message = (
                    "连接器材服务失败，本次尚未发起操作。"
                )

            payload = {
                "is_error": True,
                "data": None,
                "text": [message],
                "outcome_unknown": call_started,
            }

    return {
        "tool": name,
        "arguments": arguments,
        "result": payload,
    }


def execute_confirmed_action(action):
    """供网页在用户点击确认按钮后调用。"""
    loop_factory = (
        asyncio.ProactorEventLoop
        if sys.platform == "win32"
        else asyncio.new_event_loop
    )

    with asyncio.Runner(
        loop_factory=loop_factory,
    ) as runner:
        return runner.run(_execute_action(action))