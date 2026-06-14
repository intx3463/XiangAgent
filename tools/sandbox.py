"""安全执行环境，用于动态创建工具（宽松模式：允许 HTTP，禁止文件系统）"""

import ast

SAFE_BUILTINS = {
    "print": print, "str": str, "int": int, "float": float, "bool": bool,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "abs": abs, "max": max, "min": min, "sum": sum, "round": round,
    "True": True, "False": False, "None": None,
    "isinstance": isinstance, "type": type, "hasattr": hasattr,
    "getattr": getattr, "setattr": setattr, "property": property,
    "super": super, "object": object, "Exception": Exception,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "AttributeError": AttributeError,
    "eval": eval, "exec": exec, "compile": compile,
}

BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib", "socket",
    "http.server", "ftplib", "smtplib", "multiprocessing",
    "threading", "ctypes", "importlib",
}


def validate_tool_code(code: str) -> tuple[bool, str]:
    """验证工具代码安全性"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误: {e}"

    has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
    if not has_function:
        return False, "代码中没有函数定义"

    has_decorator = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == "tool":
                    has_decorator = True
                elif isinstance(dec, ast.Attribute) and dec.attr == "tool":
                    has_decorator = True
    if not has_decorator:
        return False, "函数没有 @tool 装饰器"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in BLOCKED_MODULES:
                    return False, f"禁止导入模块: {module}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module in BLOCKED_MODULES:
                    return False, f"禁止导入模块: {module}"

    return True, "验证通过"


def _safe_import(name: str, *args, **kwargs):
    """安全的 import 函数，只允许白名单模块"""
    top_module = name.split(".")[0]
    if top_module in BLOCKED_MODULES:
        raise ImportError(f"禁止导入模块: {top_module}")
    return __import__(name, *args, **kwargs)


def safe_exec_tool(code: str, tool_name: str):
    """安全执行工具代码，返回工具函数"""
    valid, msg = validate_tool_code(code)
    if not valid:
        raise ValueError(f"代码验证失败: {msg}")

    builtins_with_import = dict(SAFE_BUILTINS)
    builtins_with_import["__import__"] = _safe_import

    safe_globals = {
        "__builtins__": builtins_with_import,
        "__name__": tool_name,
    }

    from langchain_core.tools import tool
    safe_globals["tool"] = tool

    import json, re, math, datetime, collections
    safe_globals.update({
        "json": json, "re": re, "math": math,
        "datetime": datetime, "collections": collections,
    })

    try:
        import requests
        safe_globals["requests"] = requests
    except ImportError:
        pass

    exec(code, safe_globals)

    from langchain_core.tools import StructuredTool
    for name, obj in safe_globals.items():
        if isinstance(obj, StructuredTool):
            return obj
        if callable(obj) and hasattr(obj, "name") and not name.startswith("_"):
            return obj

    raise ValueError("执行代码后未找到工具函数")
