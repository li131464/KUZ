#!/usr/bin/env python3
"""
拖拽操作模块
负责执行拖拽选择和复制操作
"""

import pyautogui
import time
import pyperclip
from typing import Optional, Dict, Any

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def execute_drag(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行拖拽步骤 - 获取拖拽坐标，执行拖拽选择，并复制内容
    
    Args:
        params: 步骤参数
        step_results: 前面步骤的结果
        api_client: API客户端实例
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        target_description = params['target_description']
        api_client.log(f"🎯 开始拖拽选择: {target_description}")
        
        # 第1步：获取拖拽坐标
        payload = {"target_description": target_description}
        success, data = api_client.call_api("/api/drag", payload)
        
        if not success:
            api_client.log("❌ 获取拖拽坐标失败")
            return False, None
        
        start_position = data['start_position']
        end_position = data['end_position']
        
        api_client.log(f"📍 拖拽坐标: 起始{start_position} → 结束{end_position}")
        
        # 第2步：执行拖拽操作
        drag_success = perform_drag_and_copy(
            start_position, 
            end_position, 
            api_client
        )
        
        if not drag_success:
            api_client.log("❌ 拖拽操作失败")
            return False, None
        
        # 第3步：获取复制的内容
        selected_text = get_clipboard_content(api_client)
        
        if not selected_text:
            api_client.log("❌ 未获取到复制的内容")
            return False, None
        
        api_client.log(f"✅ 拖拽选择完成，获取内容: {selected_text[:50]}...")
        
        return True, {
            "selected_text": selected_text,
            "start_position": start_position,
            "end_position": end_position,
            "target_description": target_description
        }
        
    except Exception as e:
        error_msg = f"❌ 拖拽步骤异常: {str(e)}"
        if api_client:
            api_client.log(error_msg)
        elif log_callback:
            log_callback(error_msg)
        return False, None


def perform_drag_and_copy(
    start_position: list,
    end_position: list,
    api_client,
    duration: float = 1.0
) -> bool:
    """
    执行拖拽选择和复制操作
    
    Args:
        start_position: 起始坐标 [x, y]
        end_position: 结束坐标 [x, y]
        api_client: API客户端实例
        duration: 拖拽持续时间
    
    Returns:
        bool: 操作是否成功
    """
    try:
        start_x, start_y = start_position
        end_x, end_y = end_position
        
        api_client.log(f"🖱️  移动到起始位置: ({start_x}, {start_y})")
        
        # 确保坐标在屏幕范围内
        screen_width, screen_height = pyautogui.size()
        if not (0 <= start_x <= screen_width and 0 <= start_y <= screen_height):
            api_client.log(f"❌ 起始坐标超出屏幕范围: ({start_x}, {start_y})")
            return False
            
        if not (0 <= end_x <= screen_width and 0 <= end_y <= screen_height):
            api_client.log(f"❌ 结束坐标超出屏幕范围: ({end_x}, {end_y})")
            return False
        
        # 移动到起始位置
        pyautogui.moveTo(start_x, start_y)
        time.sleep(0.5)  # 短暂等待
        
        api_client.log(f"📐 开始拖拽到结束位置: ({end_x}, {end_y})")
        
        # 执行拖拽操作（显式使用左键，避免button参数异常）
        try:
            # 方式一：显式按下-拖动-抬起，兼容性更好
            pyautogui.mouseDown(x=start_x, y=start_y, button='left')
            time.sleep(0.1)
            pyautogui.moveTo(end_x, end_y, duration=duration)
            time.sleep(0.1)
            pyautogui.mouseUp(x=end_x, y=end_y, button='left')
        except Exception:
            # 方式二：回退到dragTo并指定button
            pyautogui.dragTo(end_x, end_y, duration=duration, button='left')
        time.sleep(0.5)  # 等待拖拽完成
        
        api_client.log("📋 执行复制操作...")
        
        # 执行复制操作 (macOS使用command，Windows/Linux使用ctrl)
        pyautogui.hotkey('command', 'c')
        time.sleep(1.0)  # 等待复制完成
        
        api_client.log("✅ 拖拽和复制操作完成")
        return True
        
    except Exception as e:
        api_client.log(f"❌ 拖拽操作异常: {str(e)}")
        return False


def get_clipboard_content(api_client) -> Optional[str]:
    """
    获取剪贴板内容
    
    Args:
        api_client: API客户端实例
    
    Returns:
        str | None: 剪贴板内容，如果失败返回None
    """
    try:
        api_client.log("📋 读取剪贴板内容...")
        
        # 使用pyperclip获取剪贴板内容
        clipboard_content = pyperclip.paste()
        
        if clipboard_content:
            api_client.log(f"✅ 成功获取剪贴板内容: {len(clipboard_content)} 字符")
            return clipboard_content.strip()
        else:
            api_client.log("⚠️  剪贴板内容为空")
            return None
            
    except Exception as e:
        api_client.log(f"❌ 读取剪贴板异常: {str(e)}")
        return None


def clear_clipboard(api_client) -> bool:
    """
    清空剪贴板
    
    Args:
        api_client: API客户端实例
    
    Returns:
        bool: 清空是否成功
    """
    try:
        api_client.log("🗑️  清空剪贴板...")
        pyperclip.copy("")
        api_client.log("✅ 剪贴板已清空")
        return True
    except Exception as e:
        api_client.log(f"❌ 清空剪贴板异常: {str(e)}")
        return False


def copy_text_to_clipboard(text: str, api_client) -> bool:
    """
    将文本复制到剪贴板
    
    Args:
        text: 要复制的文本
        api_client: API客户端实例
    
    Returns:
        bool: 复制是否成功
    """
    try:
        api_client.log(f"📋 复制文本到剪贴板: {text[:50]}...")
        pyperclip.copy(text)
        api_client.log("✅ 文本已复制到剪贴板")
        return True
    except Exception as e:
        api_client.log(f"❌ 复制到剪贴板异常: {str(e)}")
        return False


def drag_with_custom_coordinates(
    start_x: int, start_y: int,
    end_x: int, end_y: int,
    api_client,
    duration: float = 1.0,
    copy_after_drag: bool = True
) -> Optional[str]:
    """
    使用自定义坐标执行拖拽的便捷函数
    
    Args:
        start_x, start_y: 起始坐标
        end_x, end_y: 结束坐标
        api_client: API客户端实例
        duration: 拖拽持续时间
        copy_after_drag: 是否在拖拽后执行复制
    
    Returns:
        str | None: 如果复制则返回剪贴板内容，否则返回空字符串
    """
    try:
        success = perform_drag_and_copy(
            [start_x, start_y], 
            [end_x, end_y], 
            api_client, 
            duration
        )
        
        if success and copy_after_drag:
            return get_clipboard_content(api_client)
        elif success:
            return ""
        else:
            return None
            
    except Exception as e:
        api_client.log(f"❌ 自定义拖拽异常: {str(e)}")
        return None