import sys
from config import config
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent
from tools import internet_search
from prompts import DEFAULT_INSTRUCTIONS


def create_agent(instructions: str = None):
    """创建单 Agent 智能体实例"""
    config.validate()

    system_prompt = instructions or DEFAULT_INSTRUCTIONS
    tools = [internet_search] if config.TAVILY_API_KEY else []

    llm = init_chat_model(config.get_model_string(), **config.get_model_kwargs())
    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    return agent


def run_single_agent():
    """单 Agent 模式"""
    agent = create_agent()

    print("单 Agent 模式已启动！输入 'quit' 退出。\n")

    while True:
        try:
            user_input = input("你: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("再见！")
                break
            if not user_input:
                continue

            result = agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })
            response = result["messages"][-1].content
            print(f"\n助手: {response}\n")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}\n")


def run_multi_agent():
    """多 Agent 模式"""
    import asyncio
    from main import main as async_main
    asyncio.run(async_main())


def main():
    """主函数 - 支持 --multi 参数切换模式"""
    if "--multi" in sys.argv:
        run_multi_agent()
    else:
        run_single_agent()


if __name__ == "__main__":
    main()