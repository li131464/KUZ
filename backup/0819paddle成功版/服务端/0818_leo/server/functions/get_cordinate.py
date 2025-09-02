from typing import Dict, Tuple
import time

def get_cordinate(target_description: str, coordinate_db: Dict[str, Tuple[int, int]]):
    """
    根据目标描述从坐标库中获取坐标。
    返回: (success, coordinates, confidence, message, execution_time)
    """
    start_time = time.time()
    try:
        if not target_description:
            execution_time = time.time() - start_time
            return (False, (0, 0), 0.0, "目标描述为空", execution_time)

        if target_description not in coordinate_db:
            execution_time = time.time() - start_time
            return (False, (0, 0), 0.0, f"未找到目标: {target_description}", execution_time)

        coordinates = coordinate_db[target_description]
        confidence = 1.0
        message = f"目标: {target_description}"
        execution_time = time.time() - start_time
        return (True, coordinates, confidence, message, execution_time)

    except Exception as e:
        execution_time = time.time() - start_time
        return (False, (0, 0), 0.0, f"内部错误: {str(e)}", execution_time)