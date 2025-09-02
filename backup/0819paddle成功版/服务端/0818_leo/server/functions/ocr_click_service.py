#!/usr/bin/env python3
"""
OCR识别点击服务模块
负责使用PaddleOCR识别文字并返回点击坐标
"""

import time
import difflib
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import tempfile
import os
import base64

def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度，返回0-1之间的值"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def find_text_with_paddleocr(
    screenshot_base64: str,
    target_text: str,
    min_similarity_threshold: float = 0.3,
    similarity_thresholds: Optional[List[float]] = None
) -> Tuple[bool, Optional[Tuple[int, int]], float, str, float, Optional[List[str]]]:
    """
    使用PaddleOCR查找目标文字并返回坐标
    
    Args:
        screenshot_base64: base64编码的截图
        target_text: 要查找的目标文字
        min_similarity_threshold: 最低相似度阈值
        similarity_thresholds: 相似度阈值列表，从高到低尝试
    
    Returns:
        (success, coordinates, confidence, message, execution_time, suggestions)
        - success: 是否找到目标
        - coordinates: 点击坐标 (x, y)，绝对像素坐标
        - confidence: 匹配置信度
        - message: 结果消息
        - execution_time: 执行耗时
        - suggestions: 相似匹配建议
    """
    start_time = time.time()
    
    if not similarity_thresholds:
        similarity_thresholds = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
        # 只保留不低于最低阈值的值
        similarity_thresholds = [t for t in similarity_thresholds if t >= min_similarity_threshold]
    
    try:
        # 动态导入PaddleOCR
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            execution_time = time.time() - start_time
            return False, None, 0.0, "PaddleOCR未安装", execution_time, None
        
        # 初始化OCR模型
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)
        
        # 解码base64图片并保存到临时文件
        try:
            image_data = base64.b64decode(screenshot_base64)
        except Exception as e:
            execution_time = time.time() - start_time
            return False, None, 0.0, f"base64解码失败: {str(e)}", execution_time, None
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            # 使用PaddleOCR识别文本
            results = ocr.ocr(temp_path, cls=True)
            
            # 检查结果是否为空
            if not results or len(results) == 0:
                execution_time = time.time() - start_time
                return False, None, 0.0, "OCR未能识别到任何文本", execution_time, None
            
            # 收集所有识别到的文本，用于生成建议
            all_texts = []
            
            # 尝试不同的相似度阈值，从高到低
            for threshold in similarity_thresholds:
                # 搜索目标文本
                best_match = None
                highest_similarity = 0
                
                for line in results:
                    if not line:  # 跳过空行
                        continue
                    for bbox, (text, ocr_confidence) in line:
                        all_texts.append(text)
                        
                        # 计算文本相似度
                        similarity = calculate_text_similarity(target_text, text)
                        
                        # 如果相似度超过当前阈值，并且比之前找到的最佳匹配相似度更高
                        if similarity >= threshold and similarity > highest_similarity:
                            highest_similarity = similarity
                            best_match = (bbox, text, ocr_confidence, similarity)
                
                # 如果找到匹配
                if best_match:
                    bbox, text, ocr_confidence, similarity = best_match
                    
                    # 计算中心点坐标 (bbox是4个点的坐标: [左上, 右上, 右下, 左下])
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    center_x = int(sum(x_coords) / 4)
                    center_y = int(sum(y_coords) / 4)
                    
                    execution_time = time.time() - start_time
                    message = f"找到文字'{text}' (相似度: {similarity:.3f}, OCR置信度: {ocr_confidence:.3f})"
                    
                    return True, (center_x, center_y), similarity, message, execution_time, None
            
            # 如果所有阈值都尝试过了还是没找到匹配，生成相似建议
            suggestions = difflib.get_close_matches(target_text, list(set(all_texts)), n=3, cutoff=0.3)
            execution_time = time.time() - start_time
            message = f"未找到与'{target_text}'相似的文本 (已尝试阈值: {similarity_thresholds[0]}-{similarity_thresholds[-1]})"
            
            return False, None, 0.0, message, execution_time, suggestions
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        execution_time = time.time() - start_time
        return False, None, 0.0, f"OCR识别过程中发生错误: {str(e)}", execution_time, None

def ocr_click_service(
    target_text: str,
    screenshot_base64: str,
    min_similarity_threshold: float = 0.3
) -> Dict[str, Any]:
    """
    OCR点击服务主函数
    
    Args:
        target_text: 要查找并点击的目标文字
        screenshot_base64: base64编码的截图
        min_similarity_threshold: 最低相似度阈值
    
    Returns:
        包含结果的字典
    """
    success, coordinates, confidence, message, execution_time, suggestions = find_text_with_paddleocr(
        screenshot_base64, target_text, min_similarity_threshold
    )
    
    result = {
        "success": success,
        "coordinates": coordinates,
        "confidence": confidence,
        "message": message,
        "execution_time": execution_time,
        "target_text": target_text
    }
    
    if suggestions:
        result["suggestions"] = suggestions
    
    return result
