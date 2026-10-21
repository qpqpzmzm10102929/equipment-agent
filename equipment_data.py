# 模拟器材库：每件实物都有唯一编号。
# 后续 Agent 会查询这些信息，再判断器材是否适合用户的需求。

EQUIPMENT = [
    {
        "id": "EQ001",
        "name": "手机三脚架 A",
        "category": "支架",
        "description": "固定手机，适合采访和录像，附带手机夹。",
    },
    {
        "id": "EQ002",
        "name": "手机三脚架 B",
        "category": "支架",
        "description": "固定手机，与手机三脚架 A 功能相同，可作为替代。",
    },
    {
        "id": "EQ003",
        "name": "双人无线麦克风",
        "category": "麦克风",
        "description": "适合双人采访，支持 USB-C 接口的手机。",
    },
    {
        "id": "EQ004",
        "name": "有线领夹麦克风",
        "category": "麦克风",
        "description": "适合单人收音，支持 USB-C 接口的手机。",
    },
    {
        "id": "EQ005",
        "name": "相机三脚架",
        "category": "支架",
        "description": "用于固定相机，不附带手机夹。",
    },
    {
        "id": "EQ006",
        "name": "便携投影仪",
        "category": "投影设备",
        "description": "适合室内活动投影，需要设备提供 HDMI 输出接口。",
    },
]


# 直接运行这个文件时，打印器材列表，检查数据是否正确。
if __name__ == "__main__":
    print(f"器材库加载成功，共 {len(EQUIPMENT)} 件器材：\n")

    for item in EQUIPMENT:
        print(f"{item['id']} | {item['name']} | {item['category']}")