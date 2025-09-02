#!/usr/bin/env python3
"""
文件操作模块
负责处理文件的保存、读取等操作
"""

import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

def save_result_to_file(
    content: str,
    filename: str,
    encoding: str = 'utf-8',
    log_callback: Optional[callable] = None
) -> bool:
    """
    将结果保存到文件
    
    Args:
        content: 要保存的内容
        filename: 文件名
        encoding: 文件编码，默认utf-8
        log_callback: 日志回调函数
    
    Returns:
        bool: 保存是否成功
    """
    try:
        if log_callback:
            log_callback(f"📁 开始保存结果到文件: {filename}")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # 保存文件
        with open(filename, 'w', encoding=encoding) as f:
            f.write(content)
        
        # 获取文件大小
        file_size = os.path.getsize(filename)
        
        if log_callback:
            log_callback(f"✅ 文件保存成功: {filename}")
            log_callback(f"📊 文件大小: {file_size} 字节")
            log_callback(f"📄 内容预览: {content[:100]}{'...' if len(content) > 100 else ''}")
        
        return True
        
    except Exception as e:
        if log_callback:
            log_callback(f"❌ 文件保存失败: {str(e)}")
        return False


def append_result_to_file(
    content: str,
    filename: str,
    encoding: str = 'utf-8',
    add_timestamp: bool = True,
    log_callback: Optional[callable] = None
) -> bool:
    """
    将结果追加到文件
    
    Args:
        content: 要追加的内容
        filename: 文件名
        encoding: 文件编码，默认utf-8
        add_timestamp: 是否添加时间戳
        log_callback: 日志回调函数
    
    Returns:
        bool: 追加是否成功
    """
    try:
        if log_callback:
            log_callback(f"📁 开始追加结果到文件: {filename}")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # 准备内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if add_timestamp:
            formatted_content = f"\n[{timestamp}]\n{content}\n" + "="*50 + "\n"
        else:
            formatted_content = f"{content}\n"
        
        # 追加到文件
        with open(filename, 'a', encoding=encoding) as f:
            f.write(formatted_content)
        
        # 获取文件大小
        file_size = os.path.getsize(filename)
        
        if log_callback:
            log_callback(f"✅ 内容追加成功: {filename}")
            log_callback(f"📊 文件大小: {file_size} 字节")
        
        return True
        
    except Exception as e:
        if log_callback:
            log_callback(f"❌ 内容追加失败: {str(e)}")
        return False


def save_json_result(
    data: Dict[str, Any],
    filename: str,
    encoding: str = 'utf-8',
    log_callback: Optional[callable] = None
) -> bool:
    """
    将结果保存为JSON文件
    
    Args:
        data: 要保存的数据字典
        filename: 文件名
        encoding: 文件编码，默认utf-8
        log_callback: 日志回调函数
    
    Returns:
        bool: 保存是否成功
    """
    try:
        import json
        
        if log_callback:
            log_callback(f"📁 开始保存JSON结果到文件: {filename}")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        # 保存JSON文件
        with open(filename, 'w', encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 获取文件大小
        file_size = os.path.getsize(filename)
        
        if log_callback:
            log_callback(f"✅ JSON文件保存成功: {filename}")
            log_callback(f"📊 文件大小: {file_size} 字节")
            log_callback(f"📊 数据项数: {len(data)} 个")
        
        return True
        
    except Exception as e:
        if log_callback:
            log_callback(f"❌ JSON文件保存失败: {str(e)}")
        return False


def read_file_content(
    filename: str,
    encoding: str = 'utf-8',
    log_callback: Optional[callable] = None
) -> Optional[str]:
    """
    读取文件内容
    
    Args:
        filename: 文件名
        encoding: 文件编码，默认utf-8
        log_callback: 日志回调函数
    
    Returns:
        str | None: 文件内容，如果失败返回None
    """
    try:
        if log_callback:
            log_callback(f"📖 开始读取文件: {filename}")
        
        if not os.path.exists(filename):
            if log_callback:
                log_callback(f"❌ 文件不存在: {filename}")
            return None
        
        with open(filename, 'r', encoding=encoding) as f:
            content = f.read()
        
        if log_callback:
            log_callback(f"✅ 文件读取成功: {filename}")
            log_callback(f"📊 内容长度: {len(content)} 字符")
        
        return content
        
    except Exception as e:
        if log_callback:
            log_callback(f"❌ 文件读取失败: {str(e)}")
        return None


def get_file_info(filename: str) -> Dict[str, Any]:
    """
    获取文件信息
    
    Args:
        filename: 文件名
    
    Returns:
        dict: 文件信息字典
    """
    info = {
        "exists": False,
        "size": 0,
        "modified_time": None,
        "created_time": None,
        "is_file": False,
        "is_dir": False
    }
    
    try:
        if os.path.exists(filename):
            info["exists"] = True
            info["size"] = os.path.getsize(filename)
            info["modified_time"] = datetime.fromtimestamp(os.path.getmtime(filename))
            info["created_time"] = datetime.fromtimestamp(os.path.getctime(filename))
            info["is_file"] = os.path.isfile(filename)
            info["is_dir"] = os.path.isdir(filename)
    except Exception:
        pass
    
    return info


# 执行文件保存步骤的函数
def execute_save_result(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行save_result步骤
    
    Args:
        params: 步骤参数
        step_results: 前面步骤的结果
        api_client: API客户端（这里不需要用到）
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        filename = params.get('filename', 'result.txt')
        
        # 获取要保存的内容
        if params.get('use_previous_result'):
            source_step = params.get('source_step')
            if source_step not in step_results:
                if log_callback:
                    log_callback(f"❌ 找不到步骤 {source_step} 的结果")
                return False, None
            
            step_result = step_results[source_step]
            content = step_result.get('processed_result', '')
            
            if not content:
                if log_callback:
                    log_callback("❌ 没有找到LLM处理结果")
                return False, None
        else:
            content = params.get('content', '')
        
        # 选择保存方式
        save_mode = params.get('save_mode', 'overwrite')  # overwrite, append, json
        
        success = False
        if save_mode == 'append':
            success = append_result_to_file(content, filename, log_callback=log_callback)
        elif save_mode == 'json':
            # 将内容包装成JSON格式
            json_data = {
                "timestamp": datetime.now().isoformat(),
                "content": content,
                "source_step": params.get('source_step'),
                "filename": filename
            }
            success = save_json_result(json_data, filename, log_callback=log_callback)
        else:  # overwrite
            success = save_result_to_file(content, filename, log_callback=log_callback)
        
        if success:
            file_info = get_file_info(filename)
            result = {
                "filename": filename,
                "content": content,
                "save_mode": save_mode,
                "file_info": file_info
            }
            return True, result
        else:
            return False, None
            
    except Exception as e:
        if log_callback:
            log_callback(f"❌ 保存结果步骤异常: {str(e)}")
        return False, None