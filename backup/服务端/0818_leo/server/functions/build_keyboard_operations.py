from typing import Optional, List, Dict, Any, Tuple
import time
from difflib import get_close_matches

def _auto_detect_clipboard(operations: List[str]) -> bool:
    ops_lower = [str(op).strip().lower() for op in operations]
    return any(op in ("command+c", "ctrl+c") for op in ops_lower)

def build_keyboard_operations(
    operation_name: Optional[str],
    operations_override: Optional[List[str]],
    keyboard_db: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any], str, float]:
    """
    去平台化版本：
    - 如果传入 operations_override，则直接使用该序列，自动判断是否包含复制操作；
    - 否则如果传入 operation_name，则从配置中直接取默认 operations（忽略 platform_variants）；
    - 两者都没有则返回失败。
    """
    start_time = time.time()

    try:
        # 路径1：直接使用传入的操作序列
        if operations_override and isinstance(operations_override, list):
            operations = operations_override
            op_name = operation_name or "键盘操作"
            payload = {
                "operation_name": op_name,
                "operations": operations,
                "has_clipboard_result": _auto_detect_clipboard(operations),
                "description": operation_name or "自定义操作序列",
            }
            exec_time = float(time.time() - start_time)
            return True, payload, f"操作: {op_name}", exec_time

        # 路径2：从配置中取默认 operations（忽略平台差异）
        if operation_name:
            if operation_name not in keyboard_db:
                available = list(keyboard_db.keys())
                # 提供相似项建议
                suggestions = get_close_matches(operation_name, available, n=3, cutoff=0.6)
                suggest_text = f"；相似项: {suggestions}" if suggestions else ""
                exec_time = float(time.time() - start_time)
                return False, {}, f"未找到键盘操作: {operation_name}，可用操作: {available}{suggest_text}", exec_time

            cfg = keyboard_db[operation_name]
            operations = cfg["operations"]
            has_clipboard_result = cfg.get("has_clipboard_result")
            if has_clipboard_result is None:
                has_clipboard_result = _auto_detect_clipboard(operations)

            payload = {
                "operation_name": cfg["operation_name"],
                "operations": operations,
                "has_clipboard_result": has_clipboard_result,
                "description": cfg["description"],
            }
            exec_time = float(time.time() - start_time)
            return True, payload, f"操作: {operation_name}", exec_time

        # 路径3：参数不足
        exec_time = float(time.time() - start_time)
        return False, {}, "缺少 operations 或 operation_name", exec_time

    except Exception as e:
        exec_time = float(time.time() - start_time)
        return False, {}, f"内部错误: {str(e)}", exec_time