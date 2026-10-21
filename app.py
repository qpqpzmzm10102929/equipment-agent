import copy
import json

import streamlit as st

from equipment_service import search_equipment
from my_reservations import list_reservations
from reservation_service import init_reservation_tables
from web_agent import ask_agent
from web_actions import execute_confirmed_action


st.set_page_config(
    page_title="借物小管家",
    page_icon="🎒",
    layout="wide",
)

for key, default in {
    "chat_messages": [],
    "agent_history": [],
    "pending_action": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def show_tool_logs(logs):
    if not logs:
        return

    with st.expander("🔧 查看工具执行记录"):
        for index, log in enumerate(logs, start=1):
            st.markdown(f"**{index}. {log['tool']}**")
            st.json({
                "参数": log["arguments"],
                "返回结果": log["result"],
            })


def add_reply(reply, logs=None):
    """同时保存页面回答和模型对话历史。"""
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": reply,
        "tool_logs": logs or [],
    })
    st.session_state.agent_history.append({
        "role": "assistant",
        "content": reply,
    })


def describe_result(log):
    """根据工具真实返回值生成执行结果提示。"""
    result = log["result"]

    if result.get("outcome_unknown"):
        return (
            "⚠️ 暂时无法确认操作是否生效。"
            "请先查看「我的预约」或让我查询预约记录，"
            "不要直接重复提交。"
        )

    if result.get("is_error"):
        details = "\n".join(result.get("text", []))
        return "❌ 操作未成功。\n\n" + (
            details or "请查看工具执行记录。"
        )

    data = result.get("data")
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]

    if not isinstance(data, dict):
        return (
            "工具已返回结果，但暂时无法解析预约状态。"
            "请查看「我的预约」确认。"
        )

    reservation_id = data.get("reservation_id", "")

    if (
        log["tool"] == "create_reservation"
        and data.get("status") == "active"
        and reservation_id
    ):
        names = "、".join(data.get("equipment_names", []))
        return (
            "✅ 预约成功！\n\n"
            f"- 器材：{names}\n"
            f"- 开始时间：{data.get('start_time', '')}\n"
            f"- 结束时间：{data.get('end_time', '')}\n"
            f"- 预约编号：`{reservation_id}`\n"
            "- 状态：有效"
        )

    if (
        log["tool"] == "cancel_reservation"
        and data.get("status") == "cancelled"
    ):
        return (
            "✅ 预约已取消。\n\n"
            f"预约编号：`{reservation_id}`\n\n"
            "器材对应时段已释放，记录保留在「我的预约」中。"
        )

    return (
        "已收到工具返回结果，请查看「我的预约」确认当前状态。"
    )


def handle_action(action_id, confirmed):
    """按钮回调：只处理当前这份待确认申请。"""
    current = st.session_state.pending_action

    # 旧按钮或已经处理过的申请，不重复执行。
    if current is None or current["id"] != action_id:
        return

    action = copy.deepcopy(current)
    st.session_state.pending_action = None

    label = (
        "创建预约"
        if action["tool"] == "create_reservation"
        else "取消预约"
    )

    user_message = (
        f"我已点击确认执行：{label}。"
        if confirmed
        else f"我已放弃这次{label}申请。"
    )

    st.session_state.chat_messages.append({
        "role": "user",
        "content": user_message,
    })
    st.session_state.agent_history.append({
        "role": "user",
        "content": user_message,
    })

    if not confirmed:
        add_reply("已放弃本次申请，没有执行操作。")
        return

    try:
        with st.spinner("正在执行，请稍候……"):
            log = execute_confirmed_action(action)
    except Exception:
        log = {
            "tool": action["tool"],
            "arguments": action["arguments"],
            "result": {
                "is_error": True,
                "outcome_unknown": True,
                "data": None,
                "text": ["执行过程异常，请先查询预约记录确认。"],
            },
        }

    # 将实际执行的工具及其返回值写入模型历史。
    call_id = "confirmed_" + action["id"]

    st.session_state.agent_history.extend([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": action["tool"],
                    "arguments": json.dumps(
                        action["arguments"],
                        ensure_ascii=False,
                    ),
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(
                log["result"],
                ensure_ascii=False,
            ),
        },
    ])

    add_reply(describe_result(log), [log])


init_reservation_tables()

with st.sidebar:
    st.title("🎒 借物小管家")
    st.caption("校园活动器材借用助手")

    st.divider()
    st.write("当前用户：演示用户")
    st.write("时间统一使用北京时间")

    st.button("刷新数据", width="stretch")

    if st.button("清空对话", width="stretch"):
        st.session_state.chat_messages = []
        st.session_state.agent_history = []
        st.session_state.pending_action = None

    st.caption("清空对话会放弃未确认申请，已保存的预约不会删除。")
    st.divider()
    st.info("支持查询器材、查询空闲、创建预约和取消预约。")


equipment = search_equipment()
reservations = list_reservations()

equipment_names = {
    item["id"]: item["name"]
    for item in equipment
}

st.title("🎒 借物小管家")
st.caption("说出你的需求，让助手帮你查询和借用校园器材。")

col1, col2, col3 = st.columns(3)
col1.metric("器材总数", len(equipment))
col2.metric(
    "有效预约",
    sum(item["status"] == "active" for item in reservations),
)
col3.metric(
    "已取消预约",
    sum(item["status"] == "cancelled" for item in reservations),
)

st.divider()

chat_tab, equipment_tab, reservation_tab = st.tabs([
    "💬 智能助手",
    "📦 器材库",
    "📋 我的预约",
])

with chat_tab:
    st.caption("支持连续追问；创建和取消预约需要点击按钮确认。")

    if not st.session_state.chat_messages:
        st.info("试着问：我要用手机拍双人采访，需要借哪些器材？")

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            show_tool_logs(message.get("tool_logs", []))

    pending = st.session_state.pending_action

    if pending is not None:
        with st.container(border=True):
            arguments = pending["arguments"]

            if pending["tool"] == "create_reservation":
                st.subheader("📝 待确认：创建预约")

                for equipment_id in arguments["equipment_ids"]:
                    name = equipment_names.get(
                        equipment_id,
                        "未知器材",
                    )
                    st.write(f"器材：{name}（{equipment_id}）")

                st.write("开始时间：" + arguments["start_time"])
                st.write("结束时间：" + arguments["end_time"])
                st.caption("提交时会再次检查是否存在时间冲突。")

            else:
                st.subheader("📝 待确认：取消预约")
                reservation_id = arguments["reservation_id"]
                st.write("预约编号：" + reservation_id)

                target = next(
                    (
                        item for item in reservations
                        if item["reservation_id"] == reservation_id
                    ),
                    None,
                )

                if target:
                    names = "、".join(
                        device["name"]
                        for device in target["equipment"]
                    )
                    st.write("器材：" + names)
                    st.write("开始时间：" + target["start_time"])
                    st.write("结束时间：" + target["end_time"])
                else:
                    st.warning("当前预约列表中未找到该编号，请核对。")

            confirm_col, abandon_col = st.columns(2)

            confirm_col.button(
                "确认执行",
                key="confirm_" + pending["id"],
                type="primary",
                width="stretch",
                on_click=handle_action,
                args=(pending["id"], True),
            )

            abandon_col.button(
                "放弃",
                key="abandon_" + pending["id"],
                width="stretch",
                on_click=handle_action,
                args=(pending["id"], False),
            )

    user_text = st.chat_input(
        "请描述你的需求",
        key="equipment_chat_input",
        max_chars=2000,
        submit_mode="disable",
        disabled=pending is not None,
    )

    if pending is not None:
        st.caption("请先确认或放弃当前申请，再继续聊天。")

    if user_text and user_text.strip():
        user_text = user_text.strip()

        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_text,
        })

        with st.chat_message("user"):
            st.markdown(user_text)

        with st.spinner("正在理解需求并查询，请稍候……"):
            result = ask_agent(
                user_text,
                st.session_state.agent_history,
            )

        st.session_state.agent_history = result["history"]
        st.session_state.pending_action = result.get(
            "pending_action"
        )
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": result["reply"],
            "tool_logs": result["tool_logs"],
        })

        st.rerun()


with equipment_tab:
    keyword = st.text_input(
        "搜索器材",
        placeholder="输入关键词，例如：麦克风、三脚架",
    )

    matched = search_equipment(keyword)

    if matched:
        st.dataframe(
            [
                {
                    "编号": item["id"],
                    "名称": item["name"],
                    "类别": item["category"],
                    "用途与限制": item["description"],
                }
                for item in matched
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("没有找到符合条件的器材。")


with reservation_tab:
    if not reservations:
        st.info("目前还没有预约记录。")
    else:
        status_names = {
            "active": "有效",
            "cancelled": "已取消",
        }

        st.dataframe(
            [
                {
                    "预约编号": item["reservation_id"],
                    "器材": "、".join(
                        device["name"]
                        for device in item["equipment"]
                    ),
                    "开始时间": item["start_time"],
                    "结束时间": item["end_time"],
                    "状态": status_names.get(
                        item["status"],
                        item["status"],
                    ),
                }
                for item in reservations
            ],
            hide_index=True,
            width="stretch",
        )