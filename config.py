import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 模型配置
    MODEL_ID = os.getenv("MODEL_ID", "mimo-v2.5-pro")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # 深度思考开关
    THINKING_DISABLED = os.getenv("THINKING_DISABLED", "true").lower() == "true"

    # Tavily 搜索配置（可选）
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # LangSmith 追踪配置（可选）
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    @classmethod
    def get_model_string(cls) -> str:
        """获取模型字符串，格式：provider:model"""
        if "openai" in cls.OPENAI_BASE_URL.lower() or "xiaomi" in cls.OPENAI_BASE_URL.lower():
            return f"openai:{cls.MODEL_ID}"
        return cls.MODEL_ID

    @classmethod
    def get_model_kwargs(cls) -> dict:
        """获取模型额外参数"""
        if cls.THINKING_DISABLED:
            return {"model_kwargs": {"extra_body": {"thinking": {"type": "disabled"}}}}
        return {}

    @classmethod
    def validate(cls):
        """验证必要配置"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 未设置")
        return True


config = Config()