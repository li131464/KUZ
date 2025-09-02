from pathlib import Path
from datetime import datetime
import importlib.util
import base64
import json
import os

def _load_ocr_module_and_server_dir():
    """
    动态加载 rec/ocr.py 模块，并返回 (ocr_module, server_dir)
    为与现有 start.py 的路径逻辑保持一致，这里计算 server_dir 后向上 3 层寻找 rec 目录。
    """
    server_dir = Path(__file__).resolve().parent.parent
    rec_dir = server_dir.parent.parent.parent / "rec"
    ocr_path = rec_dir / "ocr.py"

    spec = importlib.util.spec_from_file_location("ocr", ocr_path)
    ocr_module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"无法加载OCR模块: {ocr_path}")
    spec.loader.exec_module(ocr_module)
    return ocr_module, server_dir

def recognize_text_from_base64(screenshot_b64: str, target_description: str) -> str:
    """
    从 base64 截图识别文本，返回识别到的字符串（与现有客户端兼容）。
    - 保存截图到文件（便于调试）
    - 调用 rec/ocr.py 的 ocr_recognize(image_path, output_dir)
    - 读取输出 JSON，提取 rec_texts 或 list[text]
    - 返回 '\n'.join(texts) 或错误描述字符串
    """
    try:
        print(f"接收到截图数据长度: {len(screenshot_b64)} 字符")
        print(f"识别目标: {target_description}")

        # 解码并保存截图
        try:
            image_bytes = base64.b64decode(screenshot_b64)
        except Exception as e:
            return f"OCR识别失败: base64解码错误 - {e}"

        server_dir: Path
        try:
            ocr_module, server_dir = _load_ocr_module_and_server_dir()
        except Exception as e:
            return f"OCR识别失败: 加载OCR模块失败 - {e}"

        # 保存截图（带时间戳，便于调试）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = server_dir / f"received_screenshot_{timestamp}.png"
        try:
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            print(f"截图已保存到: {image_path}")
        except Exception as e:
            return f"OCR识别失败: 保存截图失败 - {e}"

        # 准备输出目录
        temp_output_dir = server_dir / "temp_ocr_output"
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        # 运行OCR识别
        try:
            ocr_module.ocr_recognize(str(image_path), str(temp_output_dir))
        except Exception as e:
            return f"OCR识别失败: OCR运行异常 - {e}"

        # 读取识别结果
        base_name = image_path.stem
        json_file = temp_output_dir / f"{base_name}.json"
        if not json_file.exists():
            return "OCR识别失败: 未生成识别结果文件"

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except Exception as e:
            return f"OCR识别失败: 结果文件解析失败 - {e}"
        finally:
            # 清理json临时文件
            try:
                json_file.unlink(missing_ok=True)
            except Exception:
                pass

        # 提取文字内容（兼容两种结构）
        recognized_texts = []
        if isinstance(ocr_data, dict) and "rec_texts" in ocr_data:
            recognized_texts = ocr_data["rec_texts"]
        elif isinstance(ocr_data, list):
            for item in ocr_data:
                text = item.get("text") if isinstance(item, dict) else None
                if text:
                    recognized_texts.append(text)

        final_text = "\n".join(recognized_texts) if recognized_texts else "未识别到文字内容"
        print(f"OCR识别结果: {final_text}")
        return final_text

    except Exception as e:
        return f"OCR识别失败: {e}"