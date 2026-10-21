import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


BASE_DIR = Path(__file__).resolve().parent


async def main():
    # 使用当前虚拟环境的 Python 启动 MCP 服务。
    server = StdioServerParameters(
        command=sys.executable,
        args=["-X", "utf8", str(BASE_DIR / "mcp_server.py")],
        cwd=str(BASE_DIR),
    )

    async with Client(server, read_timeout_seconds=30) as client:
        # 第一步：通过 MCP 获取服务提供的工具。
        tools_result = await client.list_tools()

        print(f"发现 {len(tools_result.tools)} 个 MCP 工具：")
        for tool in tools_result.tools:
            print(f"- {tool.name}")

        # 第二步：通过 MCP 调用器材查询工具。
        print("\n正在通过 MCP 查询：麦克风")

        result = await client.call_tool(
            "search_equipment",
            {"keyword": "麦克风"},
        )

        if result.is_error:
            print("工具调用失败：")
            for block in result.content:
                if block.type == "text":
                    print(block.text)
            return

        print("工具调用成功，返回结果：")

        if result.structured_content is not None:
            print(json.dumps(
                result.structured_content,
                ensure_ascii=False,
                indent=2,
            ))
        else:
            for block in result.content:
                if block.type == "text":
                    print(block.text)

    print("\n测试结束，MCP 连接已关闭。")


if __name__ == "__main__":
    asyncio.run(main())