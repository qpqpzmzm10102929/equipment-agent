from database import get_connection, init_database


def search_equipment(keyword: str = "") -> list[dict]:
    """按关键词查询器材，留空则返回全部器材。"""
    keyword = keyword.strip()

    with get_connection() as connection:
        if not keyword:
            rows = connection.execute(
                "SELECT * FROM equipment ORDER BY id"
            ).fetchall()
        else:
            # 使用问号传入参数，避免把用户输入拼接进 SQL。
            # instr 用来判断字段中是否包含关键词。
            rows = connection.execute("""
                SELECT *
                FROM equipment
                WHERE instr(lower(id), lower(?)) > 0
                   OR instr(name, ?) > 0
                   OR instr(category, ?) > 0
                   OR instr(description, ?) > 0
                ORDER BY id
            """, (keyword, keyword, keyword, keyword)).fetchall()

    # 转成普通字典，方便后续通过 MCP 返回给 Agent。
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_database()

    keyword = input("请输入器材关键词（直接回车查看全部）：")
    results = search_equipment(keyword)

    if not results:
        print("没有找到匹配的器材，请换一个关键词。")
    else:
        print(f"\n找到 {len(results)} 件器材：\n")

        for item in results:
            print(f"{item['id']} | {item['name']}")
            print(f"类别：{item['category']}")
            print(f"说明：{item['description']}")
            print("-" * 40)