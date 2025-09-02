"""
图像识别和截图相关操作
"""

import pyautogui
import base64
from io import BytesIO
from .api_client import APIClient

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def get_screenshot_coordinates(params, api_client):
    """
    执行rec_get_xy步骤 - 获取截图区域坐标
    
    Args:
        params: 参数字典，包含target_description
        api_client: API客户端实例
    
    Returns:
        (success, result): 成功标志和结果数据
    """
    target_description = params['target_description']
    payload = {"target_description": target_description}
    
    success, data = api_client.call_api("/api/rec/get_xy", payload)
    if success:
        upleft = data['upleft']
        downright = data['downright']
        api_client.log(f"   坐标: 左上{upleft} 右下{downright}")
        return True, {"upleft": upleft, "downright": downright}
    else:
        return False, None


def recognize_screenshot(params, step_results, api_client):
    """
    执行rec_rec步骤 - 图像识别
    
    Args:
        params: 参数字典，包含target_description
        step_results: 前面步骤的结果
        api_client: API客户端实例
    
    Returns:
        (success, result): 成功标志和结果数据
    """
    target_description = params['target_description']
    
    # 查找最近的rec_get_xy步骤的结果
    coords_result = None
    for step_id in sorted(step_results.keys(), reverse=True):
        result = step_results[step_id]
        if 'upleft' in result and 'downright' in result:
            coords_result = result
            break
    
    if not coords_result:
        api_client.log("   错误: 需要先执行rec_get_xy步骤获取截图坐标")
        return False, None
    
    api_client.log(f"   使用坐标: 左上{coords_result['upleft']} 右下{coords_result['downright']}")
    
    # 进行截图
    screenshot_base64 = take_screenshot(coords_result['upleft'], coords_result['downright'], api_client)
    if not screenshot_base64:
        return False, None
    
    # 进行识别
    payload = {
        "screenshot": screenshot_base64,
        "target_description": target_description
    }
    
    success, data = api_client.call_api("/api/rec/rec", payload, timeout=15)
    if success:
        recognized_text = data
        api_client.log(f"   识别结果: '{recognized_text}'")
        return True, {"recognized_text": recognized_text}
    else:
        return False, None


def take_screenshot(upleft, downright, api_client=None):
    """
    进行截图并转换为base64
    
    Args:
        upleft: 左上角坐标 [x, y]
        downright: 右下角坐标 [x, y]
        api_client: API客户端实例（可选，用于日志）
    
    Returns:
        str: base64编码的截图数据，失败返回None
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        x1, y1 = upleft
        x2, y2 = downright
        width = x2 - x1
        height = y2 - y1
        
        if width <= 0 or height <= 0:
            log("❌ 无效的截图区域")
            return None
        
        # 使用pyautogui截图
        screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
        
        # 转换为base64
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        screenshot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        log(f"📸 截图完成: {width}x{height} 像素")
        return screenshot_base64
        
    except Exception as e:
        log(f"❌ 截图错误: {str(e)}")
        return None