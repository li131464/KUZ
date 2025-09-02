"""
点击和输入相关操作
"""

import pyautogui
import time
from .api_client import APIClient
import pyperclip

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def execute_click(params, api_client):
    """
    执行click步骤 - 获取坐标并点击
    
    Args:
        params: 参数字典，包含target_description
        api_client: API客户端实例
    
    Returns:
        (success, result): 成功标志和结果数据
    """
    target_description = params['target_description']
    payload = {"target_description": target_description}
    
    success, data = api_client.call_api("/api/click/xy", payload)
    if success:
        coordinates = data['coordinates']
        
        # 执行点击
        click_success = click_position(coordinates, api_client)
        if click_success:
            return True, {"coordinates": coordinates}
        else:
            return False, None
    else:
        return False, None


def execute_input(params, step_results, api_client):
    """
    执行input步骤 - 输入文字
    
    Args:
        params: 参数字典
        step_results: 前面步骤的结果
        api_client: API客户端实例
    
    Returns:
        (success, result): 成功标志和结果数据
    """
    if params.get('use_previous_result'):
        # 使用前面步骤的结果
        source_step = params['source_step']
        step_result = step_results.get(source_step)
        if not step_result:
            api_client.log(f"   错误: 找不到步骤{source_step}的结果")
            return False, None
        
        text = step_result.get('recognized_text', '')
        if not text:
            api_client.log("   错误: 没有找到识别的文字")
            return False, None
    else:
        text = params.get('text', '')
    
    # 检查是否需要按回车键
    press_enter = params.get('press_enter', False)
    
    # 执行输入
    success = input_text(text, api_client, press_enter=press_enter)
    if success:
        return True, {"input_text": text, "press_enter": press_enter}
    else:
        return False, None


def click_position(coordinates, api_client=None):
    """
    点击指定位置
    
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
        log(f"准备点击坐标: ({x}, {y})")
        
        time.sleep(0.5)  # 短暂等待
        
        # 确保点击位置在屏幕范围内
        screen_width, screen_height = pyautogui.size()
        if 0 <= x <= screen_width and 0 <= y <= screen_height:
            pyautogui.click(x, y)
            log(f"✅ 已点击坐标: ({x}, {y})")
            return True
        else:
            log(f"❌ 坐标超出屏幕范围: ({x}, {y})")
            return False
        
    except Exception as e:
        log(f"❌ 点击错误: {str(e)}")
        return False


def input_text(text, api_client=None, press_enter=False):
    """
    输入文字
    
    Args:
        text: 要输入的文字
        api_client: API客户端实例（可选，用于日志）
        press_enter: 是否在输入后按回车键
    
    Returns:
        bool: 输入是否成功
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        log("等待1秒确保输入框获得焦点...")
        time.sleep(1.0)  # 等待1秒让点击生效并确保输入框获得焦点
        
        log("清空并粘贴输入内容...")
        # 选中全部 (Windows系统使用ctrl+a)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)

        # 复制到剪贴板
        pyperclip.copy(text)
        time.sleep(0.1)

        # 粘贴 (Windows系统使用ctrl+v)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        
        # 如果需要按回车键
        if press_enter:
            log("按下回车键...")
            pyautogui.press('enter')
            time.sleep(0.5)  # 短暂等待确保按键生效
            log("✅ 已按下回车键")
        
        log("✅ 粘贴输入完成")
        return True
        
    except Exception as e:
        log(f"❌ 输入错误: {str(e)}")
        return False