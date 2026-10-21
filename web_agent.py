import asyncio
import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from openai import (
    AsyncOpenAI,
    APIConnectionError,
    APIStatusError,
)

from agent import SYSTEM_PROMPT, CHINA_TIME
from web_actions import unpack_result


BASE_DIR = Path(__file__).resolve().parent

QUERY_TOOLS = {
    "search_equipment",
    "check_availability",
    "list_reservations",
}

WRITE_TOOLS = {
    "create_reservation",
    "cancel_reservation",
}

ALLOWED_TOOLS = QUERY_TOOLS | WRITE_TOOLS

WEB_RULES = """
网页补充规则：
1. active 表示有效预约，不表示器材正在使用。
2. 查询操作可以直接执行。
3. 用户明确要求预约，且器材和时间齐全时，
   先查询空闲情况，再调用 create_reservation 提出预约申请。
4. 用户明确要求取消时，先查询预约记录，确定目标编号，
   再调用 cancel_reservation 提出取消申请。
5. 网页会拦截这两个写入工具，生成待确认操作，
   只有用户点击网页确认按钮才会真正执行。
6. 提出申请前不必要求用户在聊天中输入 y。
7. awaiting_confirmation 仅表示等待确认，绝不表示操作成功。
8. 每轮最多提出一项写入操作；多件器材应放在同一张预约单中。
9. 用户只是咨询空闲情况时，不要提出预约申请。
"""


def prepare_action(name, arguments):
    """检查并整理待确认参数，不执行数据库写入。"""
    if name == "create_reservation":
        required = {
            "equipment_ids",
            "start_time",
            "end_time",
        }
        if set(arguments) != required:
            raise ValueError("预约参数应包含器材编号、开始和结束时间。")

        ids = arguments["equipment_ids"]
        if (
            not isinstance(ids, list)
            or not ids
            or any(
                not isinstance(item, str) or not item.strip()
                for item in ids
            )
        ):
            raise ValueError("请提供有效的器材编号列表。")

        ids = [item.strip().upper() for item in ids]
        if len(ids) != len(set(ids)):
            raise ValueError("同一张预约单不能重复包含同一件器材。")

        times = []
        for field in ("start_time", "end_time"):
            value = arguments[field]
            if not isinstance(value, str):
                raise ValueError("时间必须是文本。")
            try:
                times.append(
                    datetime.strptime(
                        value.strip(),
                        "%Y-%m-%d %H:%M",
                    )
                )
            except ValueError:
                raise ValueError(
                    "时间格式应为 YYYY-MM-DD HH:MM。"
                ) from None

        if times[0] >= times[1]:
            raise ValueError("结束时间必须晚于开始时间。")

        arguments = {
            "equipment_ids": ids,
            "start_time": times[0].strftime("%Y-%m-%d %H:%M"),
            "end_time": times[1].strftime("%Y-%m-%d %H:%M"),
        }

    elif name == "cancel_reservation":
        if set(arguments) != {"reservation_id"}:
            raise ValueError("取消预约需要完整的预约编号。")

        reservation_id = arguments["reservation_id"]
        if (
            not isinstance(reservation_id, str)
            or not reservation_id.strip()
        ):
            raise ValueError("预约编号不能为空。")

        arguments = {
            "reservation_id": reservation_id.strip(),
        }

    else:
        raise ValueError("不支持的待确认操作。")

    return {
        "id": uuid4().hex,
        "tool": name,
        "arguments": arguments,
    }


async def _ask_agent(user_text, history):
    messages = copy.deepcopy(history)
    tool_logs = []
    pending_action = None

    if not messages:
        messages = [{"role": "system", "content": ""}]

    now = datetime.now(CHINA_TIME).strftime("%Y-%m-%d %H:%M")
    messages[0]["content"] = (
        SYSTEM_PROMPT
        + WEB_RULES
        + f"\n当前北京时间：{now}"
    )
    messages.append({
        "role": "user",
        "content": user_text,
    })

    def finish(reply):
        messages.append({
            "role": "assistant",
            "content": reply,
        })
        return {
            "reply": reply,
            "history": messages,
            "tool_logs": tool_logs,
            "pending_action": pending_action,
        }

    load_dotenv(
        BASE_DIR / ".env",
        encoding="utf-8-sig",
    )
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if not key:
        return finish("没有读取到模型密钥，请检查本地 .env 配置。")

    server = StdioServerParameters(
        command=sys.executable,
        args=[
            "-X",
            "utf8",
            str(BASE_DIR / "mcp_server.py"),
        ],
        cwd=str(BASE_DIR),
    )

    try:
        async with Client(
            server,
            read_timeout_seconds=30,
        ) as mcp_client:
            tool_list = await mcp_client.list_tools()

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
                for tool in tool_list.tools
                if tool.name in ALLOWED_TOOLS
            ]

            async with AsyncOpenAI(
                api_key=key,
                base_url="https://api.deepseek.com",
                timeout=60,
                max_retries=0,
            ) as model_client:
                for step in range(6):
                    response = await model_client.chat.completions.create(
                        model="deepseek-flash",
                        messages=messages,
                        tools=tools,
                        tool_choice="none" if step == 5 else "auto",
                        max_tokens=1500,
                        extra_body={
                            "thinking": {"type": "disabled"},
                        },
                    )

                    message = response.choices[0].message
                    calls = message.tool_calls or []

                    if not calls:
                        return finish(
                            message.content or "本次没有生成文字回复。"
                        )

                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            call.model_dump(exclude_none=True)
                            for call in calls
                        ],
                    })

                    for call in calls:
                        name = call.function.name
                        arguments = {}

                        try:
                            if name not in ALLOWED_TOOLS:
                                raise ValueError("不支持该工具。")

                            arguments = json.loads(
                                call.function.arguments
                            )
                            if not isinstance(arguments, dict):
                                raise ValueError("工具参数必须是对象。")

                            if name in WRITE_TOOLS:
                                # 写入请求只生成提案，不调用 MCP 写入工具。
                                if pending_action is not None:
                                    raise ValueError(
                                        "已有待确认操作，本轮不再新增操作。"
                                    )

                                pending_action = prepare_action(
                                    name,
                                    arguments,
                                )
                                payload = {
                                    "status": "awaiting_confirmation",
                                    "executed": False,
                                    "message": "等待用户点击网页确认按钮。",
                                }

                            else:
                                result = await mcp_client.call_tool(
                                    name,
                                    arguments,
                                )
                                payload = unpack_result(result)

                                # 此处只记录真正执行过的查询。
                                tool_logs.append({
                                    "tool": name,
                                    "arguments": arguments,
                                    "result": payload,
                                })

                        except ValueError as error:
                            payload = {
                                "is_error": True,
                                "message": str(error),
                            }

                        except Exception:
                            payload = {
                                "is_error": True,
                                "message": "工具查询失败，请稍后重试。",
                            }

                        # 为每个工具调用补齐对应的响应。
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                payload,
                                ensure_ascii=False,
                            ),
                        })

                    if pending_action is not None:
                        label = (
                            "创建预约"
                            if pending_action["tool"] == "create_reservation"
                            else "取消预约"
                        )
                        return finish(
                            f"已准备好“{label}”申请，尚未执行。"
                            "请核对待确认信息，再点击网页确认按钮。"
                        )

        return finish("已达到本轮查询上限，请缩小问题范围。")

    except APIConnectionError:
        return finish("模型连接失败或超时，请稍后重试。")

    except APIStatusError as error:
        return finish(
            f"模型请求失败，HTTP 状态码：{error.status_code}。"
        )

    except Exception:
        return finish("服务连接异常，请检查 MCP 服务后重试。")


def ask_agent(user_text, history):
    loop_factory = (
        asyncio.ProactorEventLoop
        if sys.platform == "win32"
        else asyncio.new_event_loop
    )

    with asyncio.Runner(
        loop_factory=loop_factory,
    ) as runner:
        return runner.run(
            _ask_agent(user_text, history)
        )