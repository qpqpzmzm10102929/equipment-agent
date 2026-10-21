import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, APIStatusError


BASE_DIR = Path(__file__).resolve().parent


def main():
    # 从项目目录读取密钥，不打印密钥内容。
    load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if not api_key:
        print("没有读取到密钥，请检查 .env 文件是否已保存。")
        return

    print("已读取密钥，正在连接 DeepSeek……")

    try:
        with OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=30.0,
            max_retries=0,
        ) as client:
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=[
                    {
                        "role": "user",
                        "content": "请只回复：DeepSeek 连接成功。",
                    }
                ],
                max_tokens=64,
                extra_body={
                    "thinking": {"type": "disabled"}
                },
            )

        reply = response.choices[0].message.content

        if reply:
            print(f"\nDeepSeek 回复：{reply}")
        else:
            print("请求已返回，但没有收到文字回复。")

    except APIConnectionError:
        print("连接失败或超时，请检查网络后重试。")

    except APIStatusError as error:
        explanations = {
            400: "请求参数有误。",
            401: "密钥验证失败，请检查密钥是否正确、有效。",
            402: "账户余额不足，请到 DeepSeek 开放平台检查余额。",
            429: "请求受到限流，请稍后重试。",
        }

        message = explanations.get(
            error.status_code,
            "接口返回错误，请记录状态码以便排查。",
        )
        print(f"请求失败：HTTP {error.status_code}，{message}")


if __name__ == "__main__":
    main()