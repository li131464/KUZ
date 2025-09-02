#!/usr/bin/env python3
"""
OCR点击操作模块
负责使用OCR识别文字并执行点击操作
"""

import pyautogui
import time
import base64
from typing import Optional, Dict, Any
from io import BytesIO

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def take_screenshot_for_ocr() -> str:
    """
    截取当前屏幕并转换为base64格式
    
    Returns:
        str: base64编码的截图
    """
    try:
        # 截取全屏
        screenshot = pyautogui.screenshot()
        
        # 转换为base64
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        screenshot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return screenshot_base64
        
    except Exception as e:
        print(f"❌ 截图失败: {str(e)}")
        return ""

def execute_ocr_click(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行OCR点击步骤
    
    Args:
        params: 步骤参数，包含target_text和min_similarity_threshold
        step_results: 前面步骤的结果
        api_client: API客户端实例
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        target_text = params.get('target_text')
        if not target_text:
            api_client.log("❌ 缺少target_text参数")
            return False, None
        
        min_similarity_threshold = params.get('min_similarity_threshold', 0.3)
        
        api_client.log(f"🔍 开始OCR识别并点击: '{target_text}' (相似度阈值: {min_similarity_threshold})")
        
        # 第1步：截取当前屏幕
        api_client.log("📸 正在截取屏幕...")
        screenshot_base64 = take_screenshot_for_ocr()
        
        if not screenshot_base64:
            api_client.log("❌ 截图失败")
            return False, None
        
        api_client.log(f"✅ 截图完成，图片大小: {len(screenshot_base64)} 字符")
        
        # 第2步：调用服务端OCR识别API
        api_client.log("🔍 正在调用OCR识别服务...")
        payload = {
            "target_text": target_text,
            "screenshot": screenshot_base64,
            "min_similarity_threshold": min_similarity_threshold
        }
        
        success, data = api_client.call_api("/api/ocr/click", payload, timeout=30)
        
        if not success:
            api_client.log("❌ OCR识别API调用失败")
            return False, None
        
        if not data.get('success'):
            message = data.get('message', '未知错误')
            suggestions = data.get('suggestions')
            
            api_client.log(f"❌ OCR未找到目标文字: {message}")
            if suggestions:
                api_client.log(f"💡 相似文字建议: {', '.join(suggestions)}")
            
            return False, None
        
        # 第3步：获取坐标并执行点击
        coordinates = data.get('coordinates')
        confidence = data.get('confidence', 0)
        message = data.get('message', '')
        
        if not coordinates:
            api_client.log("❌ 未获取到有效坐标")
            return False, None
        
        x, y = coordinates
        api_client.log(f"✅ OCR识别成功: {message}")
        api_client.log(f"📍 目标坐标: ({x}, {y}), 置信度: {confidence:.3f}")
        
        # 第4步：执行点击
        click_success = click_coordinates(coordinates, api_client)
        
        if click_success:
            api_client.log(f"✅ OCR点击完成: '{target_text}'")
            return True, {
                "target_text": target_text,
                "coordinates": coordinates,
                "confidence": confidence,
                "message": message
            }
        else:
            api_client.log("❌ 点击操作失败")
            return False, None
            
    except Exception as e:
        error_msg = f"❌ OCR点击步骤异常: {str(e)}"
        if api_client:
            api_client.log(error_msg)
        elif log_callback:
            log_callback(error_msg)
        return False, None

def click_coordinates(coordinates, api_client=None):
    """
    点击指定坐标
    
    Args:
        coordinates: 坐标 [x, y]
        api_client: API客户端实例（可选，用于日志）
    
    Returns:
        bool: 点击是否成功
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        x, y = coordinates
        log(f"🎯 准备点击坐标: ({x}, {y})")
        
        # 确保点击位置在屏幕范围内
        screen_width, screen_height = pyautogui.size()
        if not (0 <= x <= screen_width and 0 <= y <= screen_height):
            log(f"❌ 坐标超出屏幕范围: ({x}, {y}), 屏幕尺寸: ({screen_width}, {screen_height})")
            return False
        
        # 移动到目标位置
        log(f"🖱️  移动鼠标到: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.5)
        
        # 短暂等待
        time.sleep(0.2)
        
        # 执行点击
        pyautogui.click()
        log(f"✅ 已点击坐标: ({x}, {y})")
        
        # 点击后等待
        time.sleep(0.5)
        
        return True
        
    except Exception as e:
        log(f"❌ 点击错误: {str(e)}")
        return False

def ocr_click_with_text(target_text: str, api_client, min_similarity_threshold: float = 0.3) -> bool:
    """
    直接使用文字进行OCR点击的便捷函数
    
    Args:
        target_text: 要查找并点击的目标文字
        api_client: API客户端实例
        min_similarity_threshold: 最低相似度阈值
    
    Returns:
        bool: 点击是否成功
    """
    try:
        params = {
            "target_text": target_text,
            "min_similarity_threshold": min_similarity_threshold
        }
        
        success, result = execute_ocr_click(params, {}, api_client)
        return success
        
    except Exception as e:
        api_client.log(f"❌ OCR点击便捷函数异常: {str(e)}")
        return False
