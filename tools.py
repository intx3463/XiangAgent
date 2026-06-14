import json
import urllib.request
import urllib.parse


def get_weather(city: str) -> str:
    # 查个城市天气，没key就用wttr.in白嫖
    encoded = urllib.parse.quote(city)
    url = f"https://wttr.in/{encoded}?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        cur = data["current_condition"][0]
        desc_cn = cur.get("lang_zh", [{}])[0].get("value", "")
        if not desc_cn:
            desc_cn = cur.get("weatherDesc", [{}])[0].get("value", city)
        return (
            f"城市：{city}\n"
            f"天气：{desc_cn}\n"
            f"温度：{cur['temp_C']}°C（体感 {cur['FeelsLikeC']}°C）\n"
            f"湿度：{cur['humidity']}%\n"
            f"风速：{cur['windspeedKmph']} km/h，风向：{cur['winddir16Point']}\n"
            f"能见度：{cur['visibility']} km"
        )
    except Exception as e:
        return f"查询天气失败：{e}"


def get_hitokoto() -> str:
    # 随机来一句名言，动漫鸡汤啥的
    url = "https://hitokoto-api.ecylt.com/api/hitokoto"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return f"「{data['content']}」—— {data['source']}"
    except Exception as e:
        return f"获取名言失败：{e}"


# 工具的 schema，给模型看的，告诉它有哪些工具能用

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气信息，包括温度、湿度、风速等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、Tokyo",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hitokoto",
            "description": "获取一条随机名言/动漫台词",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    # 工具调度中心，收到啥调啥
    if name == "get_weather":
        return get_weather(args.get("city", ""))
    elif name == "get_hitokoto":
        return get_hitokoto()
    else:
        return f"未知工具：{name}"
