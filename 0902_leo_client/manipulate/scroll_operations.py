#!/usr/bin/env python3
"""
滚动操作模块
负责执行页面滚动操作，支持自定义滚动次数和距离
"""

import pyautogui
import time
from typing import Optional, Dict, Any

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def execute_scroll(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行滚动步骤
    
    Args:
        params: 步骤参数，包含scroll_description
        step_results: 前面步骤的结果
        api_client: API客户端实例
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        # 支持两种方式：直接参数或通过API获取
        if 'clicks' in params and 'direction' in params:
            # 方式1：直接从params中获取参数
            clicks = params['clicks']
            direction = params['direction']
            scroll_distance = params.get('scroll_distance', 3)
            description = f"滚动 {clicks} 次，方向 {direction}，距离 {scroll_distance}"
            
            api_client.log(f"🖱️ 开始直接滚动操作: {description}")
            
        elif 'scroll_description' in params:
            # 方式2：通过API获取滚动参数
            scroll_description = params['scroll_description']
            api_client.log(f"🖱️ 开始滚动操作: {scroll_description}")
            
            # 获取滚动参数
            payload = {"scroll_description": scroll_description}
            success, data = api_client.call_api("/api/scroll", payload)
            
            if not success:
                api_client.log("❌ 获取滚动参数失败")
                return False, None
            
            scroll_params = data['scroll_params']
            clicks = scroll_params['clicks']
            direction = scroll_params['direction']
            scroll_distance = scroll_params.get('scroll_distance', 3)
            description = scroll_params.get('description', '')
        else:
            api_client.log("❌ 缺少滚动参数 (需要 clicks+direction 或 scroll_description)")
            return False, None
        
        api_client.log(f"📋 滚动参数: 方向={direction}, 次数={clicks}, 距离={scroll_distance}")
        if description:
            api_client.log(f"📝 滚动说明: {description}")
        
        # 第2步：执行滚动操作
        scroll_success = perform_scroll_operation(
            clicks, 
            direction, 
            scroll_distance, 
            api_client
        )
        
        if not scroll_success:
            api_client.log("❌ 滚动操作执行失败")
            return False, None
        
        api_client.log(f"✅ 滚动操作完成: {description}")
        
        result = {
            "scroll_description": params.get('scroll_description', ''),
            "clicks": clicks,
            "direction": direction,
            "scroll_distance": scroll_distance,
            "description": description,
            "debug_info": f"滚动{clicks}次，方向{direction}，距离{scroll_distance}"
        }
        
        return True, result
        
    except Exception as e:
        error_msg = f"❌ 滚动操作异常: {str(e)}"
        if api_client:
            api_client.log(error_msg)
        elif log_callback:
            log_callback(error_msg)
        return False, None


def perform_scroll_operation(
    clicks: int,
    direction: str,
    scroll_distance: int,
    api_client,
    scroll_delay: float = 0.5
) -> bool:
    """
    执行具体的滚动操作
    
    Args:
        clicks: 滚动次数
        direction: 滚动方向 ("up", "down", "left", "right")
        scroll_distance: 每次滚动的距离
        api_client: API客户端实例
        scroll_delay: 滚动间隔时间
    
    Returns:
        bool: 操作是否成功
    """
    try:
        api_client.log(f"🔄 执行滚动: {direction} 方向, {clicks} 次, 每次 {scroll_distance} 单位")
        
        # 确定滚动方向的符号
        if direction.lower() == "down":
            scroll_amount = -scroll_distance  # 向下滚动为负值
        elif direction.lower() == "up":
            scroll_amount = scroll_distance   # 向上滚动为正值
        elif direction.lower() == "left":
            # 水平滚动（某些应用支持）
            scroll_amount = scroll_distance
        elif direction.lower() == "right":
            scroll_amount = -scroll_distance
        else:
            api_client.log(f"❌ 不支持的滚动方向: {direction}")
            return False
        
        # 执行滚动操作
        for i in range(clicks):
            api_client.log(f"🔄 执行第 {i+1}/{clicks} 次滚动")
            
            try:
                if direction.lower() in ["up", "down"]:
                    # 垂直滚动
                    pyautogui.scroll(scroll_amount)
                else:
                    # 水平滚动（使用hscroll，如果支持的话）
                    try:
                        pyautogui.hscroll(scroll_amount)
                    except AttributeError:
                        api_client.log("⚠️ 当前系统不支持水平滚动，跳过")
                        continue
                
                # 滚动间隔
                if i < clicks - 1:  # 最后一次滚动后不延迟
                    time.sleep(scroll_delay)
                    
            except Exception as scroll_error:
                api_client.log(f"❌ 第 {i+1} 次滚动失败: {str(scroll_error)}")
                return False
        
        api_client.log("✅ 所有滚动操作执行完成")
        return True
        
    except Exception as e:
        api_client.log(f"❌ 滚动操作异常: {str(e)}")
        return False


def scroll_to_load_content(
    api_client,
    max_scrolls: int = 10,
    scroll_distance: int = 3,
    load_delay: float = 1.0
) -> bool:
    """
    智能滚动加载页面内容的便捷函数
    
    Args:
        api_client: API客户端实例
        max_scrolls: 最大滚动次数
        scroll_distance: 滚动距离
        load_delay: 加载等待时间
    
    Returns:
        bool: 操作是否成功
    """
    try:
        api_client.log(f"🔄 开始智能滚动加载内容，最多 {max_scrolls} 次")
        
        for i in range(max_scrolls):
            api_client.log(f"🔄 滚动加载第 {i+1}/{max_scrolls} 次")
            
            # 向下滚动
            pyautogui.scroll(-scroll_distance)
            
            # 等待内容加载
            time.sleep(load_delay)
            
            # 这里可以添加检测页面是否已经加载完成的逻辑
            # 比如检测页面高度变化、特定元素出现等
            
        api_client.log("✅ 智能滚动加载完成")
        return True
        
    except Exception as e:
        api_client.log(f"❌ 智能滚动异常: {str(e)}")
        return False


def scroll_with_custom_params(
    direction: str,
    clicks: int,
    scroll_distance: int,
    api_client,
    delay_between_scrolls: float = 0.5
) -> bool:
    """
    使用自定义参数执行滚动的便捷函数
    
    Args:
        direction: 滚动方向
        clicks: 滚动次数
        scroll_distance: 滚动距离
        api_client: API客户端实例
        delay_between_scrolls: 滚动间隔
    
    Returns:
        bool: 操作是否成功
    """
    try:
        return perform_scroll_operation(
            clicks, 
            direction, 
            scroll_distance, 
            api_client, 
            delay_between_scrolls
        )
    except Exception as e:
        api_client.log(f"❌ 自定义滚动异常: {str(e)}")
        return False


def get_screen_dimensions():
    """
    获取屏幕尺寸信息
    
    Returns:
        tuple: (width, height)
    """
    return pyautogui.size()


def validate_scroll_parameters(direction: str, clicks: int, scroll_distance: int) -> bool:
    """
    验证滚动参数是否有效
    
    Args:
        direction: 滚动方向
        clicks: 滚动次数
        scroll_distance: 滚动距离
    
    Returns:
        bool: 参数是否有效
    """
    valid_directions = ["up", "down", "left", "right"]
    
    if direction.lower() not in valid_directions:
        return False
    
    if clicks <= 0 or clicks > 100:  # 限制滚动次数范围
        return False
    
    if scroll_distance <= 0 or scroll_distance > 20:  # 限制滚动距离范围
        return False
    
    return True
