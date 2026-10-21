import hashlib
import hmac
import os
import runpy
from pathlib import Path

import streamlit as st


# 密钥和组内口令由部署平台的 Secrets 提供。
try:
    team_password = st.secrets["TEAM_PASSWORD"]
    api_key = st.secrets["DEEPSEEK_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("请先在部署平台配置 TEAM_PASSWORD 和 DEEPSEEK_API_KEY。")
    st.stop()

if (
    not isinstance(team_password, str)
    or not team_password.strip()
    or not isinstance(api_key, str)
    or not api_key.strip()
):
    st.error("组内口令或模型密钥未正确配置。")
    st.stop()

# 修改平台中的口令后，旧会话需要重新登录。
password_digest = hashlib.sha256(
    team_password.encode("utf-8")
).hexdigest()

authenticated = hmac.compare_digest(
    str(st.session_state.get("_team_auth_digest", "")),
    password_digest,
)

if not authenticated:
    st.title("🎒 借物小管家")
    st.caption("小组演示入口，请输入组内访问口令。")

    with st.form("team_login"):
        entered_password = st.text_input(
            "访问口令",
            type="password",
            key="_team_password_input",
        )
        submitted = st.form_submit_button("进入智能体")

    if submitted:
        if hmac.compare_digest(
            entered_password.encode("utf-8"),
            team_password.encode("utf-8"),
        ):
            st.session_state["_team_auth_digest"] = password_digest
            st.rerun()
        else:
            st.error("口令不正确，请重新输入。")

    st.stop()

# 登录后清理输入框中的明文口令。
st.session_state.pop("_team_password_input", None)

# 让现有 Agent 代码通过环境变量读取模型密钥。
os.environ["DEEPSEEK_API_KEY"] = api_key.strip()

# 验证通过后运行原来的完整应用。
app_path = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
