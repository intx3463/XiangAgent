from langchain_core.tools import tool
import re

@tool
def calculator(expression: str) -> str:
    """计算数学表达式的工具。支持 +, -, *, / 和括号。
    Args:
        expression: 数学表达式字符串，如 '2+3' 或 '(10-5)*2'
    Returns:
        计算结果字符串"""
    # 输入验证：只允许数字、运算符、括号和空格
    safe_pattern = r'^[0-9+\-*/(). ]+$'
    if not re.match(safe_pattern, expression):
        return '错误：表达式包含不允许的字符'
    try:
        result = eval(expression)
        return f'{expression} = {result}'
    except ZeroDivisionError:
        return '错误：除以零'
    except Exception as e:
        return f'计算错误：{str(e)}'