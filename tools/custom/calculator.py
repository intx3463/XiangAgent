from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """
    计算数学表达式的工具。
    支持基本运算符：+, -, *, /，以及括号。
    
    Args:
        expression: 要计算的数学表达式，如 '30*69+78'、'(10+5)*2'
    
    Returns:
        计算结果的字符串表示
    """
    try:
        # 安全地计算数学表达式
        # 只允许数字、运算符、括号和空格
        import re
        # 检查表达式是否只包含安全字符
        safe_pattern = r'^[0-9+\-*/(). ]+$'
        if not re.match(safe_pattern, expression):
            return '错误：表达式包含不允许的字符'
        
        # 使用 eval 计算（在受限环境中）
        result = eval(expression)
        return f'{expression} = {result}'
    except ZeroDivisionError:
        return '错误：除以零'
    except SyntaxError:
        return '错误：表达式语法不正确'
    except Exception as e:
        return f'计算错误：{str(e)}'