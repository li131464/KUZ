#!/usr/bin/env python3
"""
等待操作模块
负责处理各种等待和延时操作
"""

import time
from typing import Optional, Dict, Any

def execute_wait(params: Dict[str, Any], step_results: Dict[int, Any], api_client, log_callback: Optional[callable] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行等待步骤
    
    Args:
        params: 步骤参数
        step_results: 前面步骤的结果
        api_client: API客户端
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        wait_time = params.get('wait_time', 1.0)  # 默认等待1秒
        reason = params.get('reason', '系统等待')
        
        if log_callback:
            log_callback(f"⏳ {reason}，等待 {wait_time} 秒...")
        elif api_client:
            api_client.log(f"⏳ {reason}，等待 {wait_time} 秒...")
        
        time.sleep(wait_time)
        
        if log_callback:
            log_callback(f"✅ 等待完成")
        elif api_client:
            api_client.log(f"✅ 等待完成")
        
        return True, {
            "wait_time": wait_time,
            "reason": reason,
            "completed_at": time.time()
        }
        
    except Exception as e:
        error_msg = f"❌ 等待步骤异常: {str(e)}"
        if log_callback:
            log_callback(error_msg)
        elif api_client:
            api_client.log(error_msg)
        return False, None


def wait_for_page_load(seconds: float = 3.0, api_client=None) -> bool:
    """
    等待页面加载
    
    Args:
        seconds: 等待时间（秒）
        api_client: API客户端实例（可选，用于日志）
    
    Returns:
        bool: 等待是否成功完成
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        log(f"⏳ 等待页面加载 {seconds} 秒...")
        time.sleep(seconds)
        log("✅ 页面加载等待完成")
        return True
    except Exception as e:
        log(f"❌ 等待异常: {str(e)}")
        return False


def wait_for_element_load(seconds: float = 2.0, element_name: str = "元素", api_client=None) -> bool:
    """
    等待元素加载
    
    Args:
        seconds: 等待时间（秒）
        element_name: 元素名称
        api_client: API客户端实例（可选，用于日志）
    
    Returns:
        bool: 等待是否成功完成
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        log(f"⏳ 等待{element_name}加载 {seconds} 秒...")
        time.sleep(seconds)
        log(f"✅ {element_name}加载等待完成")
        return True
    except Exception as e:
        log(f"❌ 等待异常: {str(e)}")
        return False


def progressive_wait(initial_wait: float = 1.0, max_attempts: int = 3, api_client=None) -> bool:
    """
    渐进式等待（用于不确定加载时间的情况）
    
    Args:
        initial_wait: 初始等待时间
        max_attempts: 最大尝试次数
        api_client: API客户端实例（可选，用于日志）
    
    Returns:
        bool: 等待是否成功完成
    """
    def log(message):
        if api_client:
            api_client.log(message)
        else:
            print(message)
    
    try:
        for attempt in range(1, max_attempts + 1):
            wait_time = initial_wait * attempt
            log(f"⏳ 第{attempt}次等待 {wait_time} 秒...")
            time.sleep(wait_time)
            
            # 这里可以添加检查逻辑，比如检查页面是否加载完成
            # 目前只是简单的等待
            
        log("✅ 渐进式等待完成")
        return True
        
    except Exception as e:
        log(f"❌ 渐进式等待异常: {str(e)}")
        return False