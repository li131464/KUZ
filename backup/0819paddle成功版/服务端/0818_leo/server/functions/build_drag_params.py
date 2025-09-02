import time
import difflib
from typing import Any, Dict, List, Optional, Tuple


def _normalize_drag_entry(entry: Any) -> Optional[Tuple[List[int], List[int]]]:
    """
    将配置项规范化为 (start_position, end_position)
    支持两种格式：
      1) {"start": [x1, y1], "end": [x2, y2]}
      2) [x1, y1, x2, y2]
    """
    try:
        if isinstance(entry, dict):
            start = entry.get("start")
            end = entry.get("end")
            if (
                isinstance(start, list) and len(start) == 2 and
                isinstance(end, list) and len(end) == 2
            ):
                return [int(start[0]), int(start[1])], [int(end[0]), int(end[1])]
        elif isinstance(entry, list) and len(entry) == 4:
            return [int(entry[0]), int(entry[1])], [int(entry[2]), int(entry[3])]
    except Exception:
        return None
    return None


def build_drag_params(
    target_description: str,
    drag_db: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[int], List[int], str, float, Optional[List[str]]]:
    """
    根据目标描述构建拖拽的起止坐标。

    返回:
        - success: 是否命中/构建成功
        - start_position: [x, y]
        - end_position: [x, y]
        - message: 文本信息
        - execution_time: 耗时
        - suggestions: 相似匹配建议（若有）

    兼容历史行为：
      - 命中内置“抖音用户信息区域” -> 返回固定坐标
      - 未命中 -> 返回一个默认拖拽区域，success=True，避免打断流程
    """
    start_time = time.time()

    # 1) 优先从 drag_db 命中（若提供）
    if drag_db:
        if target_description in drag_db:
            normalized = _normalize_drag_entry(drag_db[target_description])
            if normalized:
                exec_time = time.time() - start_time
                return True, normalized[0], normalized[1], f"拖拽: {target_description}", exec_time, None

        # 没命中时给出相似建议（Top-3）
        candidates = list(drag_db.keys())
        suggestions = difflib.get_close_matches(target_description, candidates, n=3, cutoff=0.5)
    else:
        suggestions = None
        return False, [], [], f"缺少drag参数", -100, None
