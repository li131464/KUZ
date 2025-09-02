from typing import Dict, Tuple
import time

def get_rec_xy(target_description: str, rec_db: Dict[str, Tuple[int, int, int, int]]):
    """
    根据目标描述从识别坐标库中获取左上右下坐标。
    返回: (success, upleft, downright, confidence, message, execution_time)
    """
    start_time = time.time()
    try:
        if not target_description:
            execution_time = time.time() - start_time
            return (False, (0, 0), (0, 0), 0.0, "目标描述为空", execution_time)

        if target_description not in rec_db:
            execution_time = time.time() - start_time
            return (False, (0, 0), (0, 0), 0.0, f"未找到目标: {target_description}", execution_time)

        coordinates = rec_db[target_description]
        print(coordinates)
        # 支持 [x1, y1, x2, y2] 格式
        if len(coordinates) == 4:
            x1, y1, x2, y2 = coordinates
            upleft = (x1, y1)
            downright = (x2, y2)
        else:
            execution_time = time.time() - start_time
            return (False, (0, 0), (0, 0), 0.0, f"坐标格式错误: {coordinates}", execution_time)

        confidence = 1.0
        message = f"目标: {target_description}"
        execution_time = time.time() - start_time
        print(True, upleft, downright, confidence, message, execution_time)
        return (True, upleft, downright, confidence, message, execution_time)

    except Exception as e:
        execution_time = time.time() - start_time
        return (False, (0, 0), (0, 0), 0.0, f"内部错误: {str(e)}", execution_time)