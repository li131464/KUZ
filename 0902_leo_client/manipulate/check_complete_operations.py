#!/usr/bin/env python3
"""
页面加载完成检查操作模块
负责通过关键字检测判断页面是否加载完成
"""

import time
import pyautogui
import pyperclip
from typing import Optional, Dict, Any, List

def execute_check_complete(params: Dict[str, Any], step_results: Dict[int, Any], api_client, log_callback: Optional[callable] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """执行页面加载完成检查"""
    try:
        # 获取参数
        target_keywords = params.get('target_keywords', [])
        max_attempts = params.get('max_attempts', 5)
        check_interval = params.get('check_interval', 1.0)
        timeout_message = params.get('timeout_message', '页面加载检查超时')
        click_position = params.get('click_position', '点击浏览器准备复制')  # 新增参数
        
        if not target_keywords:
            error_msg = "❌ 缺少target_keywords参数"
            if log_callback:
                log_callback(error_msg)
            return False, None
        
        if log_callback:
            log_callback(f"🔍 开始检查页面加载状态，目标关键字: {target_keywords}")
            log_callback(f"📊 最大尝试次数: {max_attempts}，检查间隔: {check_interval}秒")
            log_callback(f"🖱️ 点击位置: {click_position}")
        
        # 先获取点击坐标
        click_coordinates = None
        
        for attempt in range(1, max_attempts + 1):
            if log_callback:
                log_callback(f"🔄 第 {attempt}/{max_attempts} 次检查...")
            
            # 1. 全选复制页面内容
            try:
                if log_callback:
                    log_callback("📋 全选并复制页面内容...")
                
                # 如果还没有坐标，先调用一次API获取
                if not click_coordinates:
                    try:
                        success, response = api_client.call_api('/api/check_complete', {
                            'content': '',  # 空内容，仅获取坐标
                            'target_keywords': target_keywords,
                            'click_position': click_position
                        })
                        if success and response:
                            click_coordinates = response.get('click_coordinates', [1406, 177])
                    except:
                        click_coordinates = [1406, 177]  # 默认坐标
                
                # 点击浏览器准备复制
                if log_callback:
                    log_callback(f"🖱️ 点击浏览器准备复制位置: {click_coordinates}")
                pyautogui.click(click_coordinates[0], click_coordinates[1])
                time.sleep(0.2)
                
                # 全选
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                
                # 复制
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                
                # 获取剪贴板内容
                clipboard_content = pyperclip.paste()
                
                if not clipboard_content:
                    if log_callback:
                        log_callback("⚠️ 剪贴板内容为空，继续下次尝试...")
                    time.sleep(check_interval)
                    continue
                
                if log_callback:
                    log_callback(f"📄 获取到页面内容，长度: {len(clipboard_content)} 字符")
                
            except Exception as e:
                if log_callback:
                    log_callback(f"❌ 复制页面内容失败: {str(e)}")
                time.sleep(check_interval)
                continue
            
            # 2. 请求服务端检查关键字
            try:
                if log_callback:
                    log_callback("🌐 请求服务端检查关键字...")
                
                success, response = api_client.call_api('/api/check_complete', {
                    'content': clipboard_content,
                    'target_keywords': target_keywords,
                    'click_position': click_position
                })
                
                if success and response and response.get('success'):
                    keywords_found = response.get('keywords_found', False)
                    found_keywords = response.get('found_keywords', [])
                    
                    if keywords_found:
                        if log_callback:
                            log_callback(f"✅ 页面加载完成！找到关键字: {found_keywords}")
                        
                        return True, {
                            "keywords_found": True,
                            "found_keywords": found_keywords,
                            "attempts_used": attempt,
                            "content_length": len(clipboard_content),
                            "completed_at": time.time()
                        }
                    else:
                        if log_callback:
                            log_callback(f"⏳ 未找到目标关键字，{check_interval}秒后重试...")
                else:
                    if log_callback:
                        log_callback(f"❌ 服务端检查失败: {response.get('message', '未知错误') if response else '无响应'}")
                
            except Exception as e:
                if log_callback:
                    log_callback(f"❌ 请求服务端异常: {str(e)}")
            
            # 如果不是最后一次尝试，等待后继续
            if attempt < max_attempts:
                time.sleep(check_interval)
        
        # 所有尝试都失败
        if log_callback:
            log_callback(f"❌ {timeout_message}，已尝试 {max_attempts} 次")
        
        return False, {
            "keywords_found": False,
            "found_keywords": [],
            "attempts_used": max_attempts,
            "timeout": True,
            "timeout_message": timeout_message
        }
        
    except Exception as e:
        error_msg = f"❌ 页面加载检查异常: {str(e)}"
        if log_callback:
            log_callback(error_msg)
        return False, None