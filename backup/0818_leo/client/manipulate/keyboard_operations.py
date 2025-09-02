#!/usr/bin/env python3
"""
键盘操作模块
负责执行各种键盘快捷键操作，如全选复制、切换标签页等
"""

import pyautogui
import time
import pyperclip
import re
from typing import Optional, Dict, Any, List

# 设置pyautogui的安全性
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # 键盘操作间隔更短


def execute_keyboard(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行键盘操作步骤
    
    Args:
        params: 步骤参数，包含operation_name
        step_results: 前面步骤的结果
        api_client: API客户端实例
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        # 直接从params中获取操作序列
        if 'operations' in params:
            operations = params['operations']
            operation_name = params.get('operation_name', '键盘操作')
            # 检查是否有真正的复制操作(command+c 或 ctrl+c)
            contains_copy_operation = any(
                op.strip().lower() in ['command+c', 'ctrl+c']
                for op in operations
            )
            
            api_client.log(f"⌨️ 开始键盘操作: {operation_name}")
            api_client.log(f"📋 操作序列: {operations}")
            api_client.log(f"📋 包含复制操作: {contains_copy_operation}")
            api_client.log(f"🔍 当前已有步骤结果: {list(step_results.keys())}")
        else:
            api_client.log("❌ 缺少operations参数")
            return False, None
        
        # 严格按 API 返回的 operations 顺序执行（不做平台判断/特殊分支）
        keyboard_success = perform_keyboard_operations(operations, api_client)
        
        if not keyboard_success:
            api_client.log("❌ 键盘操作执行失败")
            return False, None
        
        # 第3步：如果操作涉及剪贴板，获取内容
        clipboard_content = None
        has_clipboard_result = False
        
        if contains_copy_operation:
            api_client.log("📋 检测到复制操作，准备获取剪贴板内容...")
            time.sleep(1.0)  # 等待剪贴板更新
            
            # 获取剪贴板内容
            clipboard_content = get_clipboard_content(api_client)
            
            if clipboard_content:
                has_clipboard_result = True
                api_client.log(f"📋 获取剪贴板内容: {len(clipboard_content)} 字符")
                # 显示内容预览，便于调试
                preview = clipboard_content[:200] + "..." if len(clipboard_content) > 200 else clipboard_content
                api_client.log(f"📄 内容预览: {preview}")
            else:
                has_clipboard_result = False
                api_client.log("⚠️ 未获取到剪贴板内容")
        
        api_client.log(f"✅ 键盘操作完成: {operation_name}")
        
        result = {
            "operation_name": operation_name,
            "operations_executed": operations,
            "has_clipboard_result": has_clipboard_result
        }
        
        if clipboard_content:
            result["clipboard_content"] = clipboard_content
        
        return True, result
        
    except Exception as e:
        error_msg = f"❌ 键盘操作异常: {str(e)}"
        if api_client:
            api_client.log(error_msg)
        elif log_callback:
            log_callback(error_msg)
        return False, None


# 辅助：归一化键名与逐键执行组合键
def _normalize_key_name(key: str) -> str:
    k = key.strip().lower()
    aliases = {
        "cmd": "command",
        "control": "ctrl",
        "option": "alt",
        "opt": "alt",
    }
    return aliases.get(k, k)

def _clear_modifier_keys(api_client) -> None:
    """
    在开始组合键之前，尝试释放所有常见修饰键，防止粘连。
    """
    try:
        api_client.log("🧹 预清理修饰键: shift/ctrl/alt/command")
        modifiers = ["shift", "ctrl", "control", "alt", "option", "command", "cmd"]
        for m in modifiers:
            try:
                pyautogui.keyUp(m)
            except Exception as e:
                # 个别平台/状态下可能抛出异常，记录告警即可
                api_client.log(f"⚠️ 清空修饰键失败: {m} -> {str(e)}")
        time.sleep(0.02)
    except Exception as e:
        api_client.log(f"⚠️ 预清理修饰键异常: {str(e)}")

def _press_combo(keys: List[str], api_client) -> bool:
    """
    逐键执行组合键：按下所有修饰键 -> 按一次主键 -> 释放修饰键（逆序）
    例如 ["command", "a"] 或 ["command", "option", "right"]
    """
    # 组合键开始前先做一次“修饰键清空”
    try:
        _clear_modifier_keys(api_client)
    except Exception as e:
        api_client.log(f"⚠️ 预清理修饰键调用异常: {str(e)}")

    norm_keys = [_normalize_key_name(k) for k in keys if k]
    if not norm_keys:
        api_client.log("❌ 组合键为空")
        return False

    main_key = norm_keys[-1]
    modifiers = norm_keys[:-1]

    try:
        # 按下修饰键
        for m in modifiers:
            api_client.log(f"🔒 按下修饰键: {m}")
            pyautogui.keyDown(m)
            time.sleep(0.02)

        # 按一次主键
        api_client.log(f"⬇️ 触发主键: {main_key}")
        pyautogui.press(main_key)
        time.sleep(0.02)

        return True
    except Exception as e:
        api_client.log(f"❌ 组合键执行异常: {' + '.join(keys)} -> {str(e)}")
        return False
    finally:
        # 释放修饰键（逆序）
        for m in reversed(modifiers):
            try:
                pyautogui.keyUp(m)
                api_client.log(f"🔓 释放修饰键: {m}")
            except Exception as e2:
                api_client.log(f"⚠️ 释放修饰键异常: {m} -> {str(e2)}")

def execute_single_operation(operation: str, api_client) -> bool:
    """
    执行单个键盘操作
    
    Args:
        operation: 操作字符串，如 "command+a", "wait:200", "enter"
        api_client: API客户端实例
    
    Returns:
        bool: 操作是否成功
    """
    try:
        operation = operation.strip()
        
        # 处理等待操作：wait:200 (毫秒)
        if operation.startswith("wait:"):
            wait_time_ms = int(operation.split(":")[1])
            wait_time_s = wait_time_ms / 1000.0
            api_client.log(f"⏳ 等待 {wait_time_s:.2f} 秒")
            time.sleep(wait_time_s)
            return True
        
        # 处理组合键操作：如 command+a, ctrl+c, command+option+right 等
        if "+" in operation:
            keys = [key.strip() for key in operation.split("+")]
            api_client.log(f"🔑 组合键(逐键执行): {' + '.join(keys)}")
            # 逐键执行：修饰键 keyDown -> 主键 press -> 修饰键 keyUp
            return _press_combo(keys, api_client)
        
        # 处理单个按键操作：enter, escape, tab 等
        api_client.log(f"🔑 单键: {operation}")
        pyautogui.press(operation)
        return True
        
    except Exception as e:
        api_client.log(f"❌ 单个操作执行异常: {operation} -> {str(e)}")
        return False


def perform_keyboard_operations(operations: List[str], api_client) -> bool:
    """
    严格按序执行一组键盘操作。
    
    Args:
        operations: 例如 ["command+a", "wait:200", "command+c"]
        api_client: API客户端实例
    
    Returns:
        bool: 全部操作成功返回 True；任何一步失败返回 False
    """
    if not isinstance(operations, list):
        api_client.log("❌ operations 参数必须是列表")
        return False
    
    for idx, op in enumerate(operations, start=1):
        if not validate_operation_format(op):
            api_client.log(f"❌ 第{idx}个操作格式非法: {op}")
            return False
        
        api_client.log(f"▶️ 执行第{idx}个操作: {op}")
        if not keyboard_operation_with_retry(op, api_client):
            api_client.log(f"❌ 第{idx}个操作执行失败: {op}")
            return False
    
    return True


def get_clipboard_content(api_client) -> Optional[str]:
    """
    获取剪贴板内容（复用drag_operations.py的实现）
    
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
            api_client.log("⚠️ 剪贴板内容为空")
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
        api_client.log("🗑️ 清空剪贴板...")
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


def validate_operation_format(operation: str) -> bool:
    """
    验证操作格式是否正确
    
    Args:
        operation: 操作字符串
    
    Returns:
        bool: 格式是否正确
    """
    if not operation or not isinstance(operation, str):
        return False
    
    operation = operation.strip()
    
    # wait:数字 格式
    if operation.startswith("wait:"):
        try:
            int(operation.split(":")[1])
            return True
        except (IndexError, ValueError):
            return False
    
    # 组合键格式 (key+key+...)
    if "+" in operation:
        keys = [key.strip() for key in operation.split("+")]
        return all(key for key in keys)  # 确保没有空字符串
    
    # 单键格式
    return bool(operation)


def keyboard_operation_with_retry(
    operation: str,
    api_client,
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> bool:
    """
    带重试机制的键盘操作
    
    Args:
        operation: 操作字符串
        api_client: API客户端实例
        max_retries: 最大重试次数
        retry_delay: 重试延迟
    
    Returns:
        bool: 操作是否成功
    """
    for attempt in range(max_retries):
        try:
            success = execute_single_operation(operation, api_client)
            if success:
                return True
            
            if attempt < max_retries - 1:
                api_client.log(f"⚠️ 操作失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            
        except Exception as e:
            if attempt < max_retries - 1:
                api_client.log(f"❌ 操作异常，{retry_delay}秒后重试: {str(e)}")
                time.sleep(retry_delay)
            else:
                api_client.log(f"❌ 操作最终失败: {str(e)}")
    
    return False