import time
import difflib
from typing import Any, Dict, List, Optional, Tuple


def build_scroll_params(
    scroll_description: str,
    scroll_db: Dict[str, Dict[str, Any]],
) -> Tuple[bool, Optional[Dict[str, Any]], str, float, Optional[List[str]]]:
    """
    根据滚动描述从配置中构建滚动参数。
    - 命中：返回 success=True, scroll_params，message="滚动: xxx"
    - 未命中：返回 success=False，并给出相似匹配建议 suggestions
    """
    start_time = time.time()
    try:
        if scroll_description not in scroll_db:
            # 相似匹配建议（Top-3）
            candidates = list(scroll_db.keys())
            suggestions = difflib.get_close_matches(
                scroll_description, candidates, n=3, cutoff=0.5
            )
            exec_time = time.time() - start_time
            return (
                False,
                None,
                f"未找到滚动参数: {scroll_description}",
                exec_time,
                suggestions or None,
            )

        cfg = scroll_db[scroll_description]
        scroll_params = {
            "clicks": cfg["clicks"],
            "x": None,
            "y": None,
            "direction": cfg["direction"],
            "scroll_distance": cfg.get("scroll_distance", 3),
            "description": cfg.get("description", ""),
        }
        exec_time = time.time() - start_time
        return True, scroll_params, f"滚动: {scroll_description}", exec_time, None

    except Exception as e:
        exec_time = time.time() - start_time
        # 将异常向上抛，由路由统一处理 500
        raise e