#!/usr/bin/env python3
"""
LLM处理操作模块
负责调用服务器端的LLM处理服务
"""

import json
from typing import Optional, Dict, Any

def execute_llm_process(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行LLM处理步骤
    
    Args:
        params: 步骤参数
        step_results: 前面步骤的结果
        api_client: API客户端实例
        log_callback: 日志回调函数
    
    Returns:
        tuple: (成功标志, 结果数据)
    """
    try:
        # 获取待处理的内容
        # 优先支持直接传入的内容（例如从服务端流程配置中引用 previous step 的 selected_text）
        content = params.get('content', '')

        # 如果没有显式 content，则尝试从 previous step 结果读取（兼容本地流程拼接）
        if not content and params.get('use_previous_result'):
            source_step = params.get('source_step')
            
            # 支持多个步骤的结果合并（同时兼容 list/tuple）
            if isinstance(source_step, (list, tuple)):
                combined_content = []
                for step_id in source_step:
                    if step_id in step_results:
                        step_result = step_results[step_id]
                        # 从执行器注入的 _step_name 读取步骤名（若存在）
                        step_name = step_result.get('_step_name', '') if isinstance(step_result, dict) else ''
                        step_content = (step_result.get('clipboard_content') or 
                                      step_result.get('selected_text') or 
                                      step_result.get('recognized_text') or
                                      step_result.get('data') or 
                                      step_result.get('processed_result') or '')
                        
                        if isinstance(step_content, dict):
                            step_content = json.dumps(step_content, ensure_ascii=False, indent=2)
                        
                        if step_content:
                            title_suffix = f" {step_name}" if step_name else ""
                            combined_content.append(f"=== 步骤{step_id}{title_suffix}结果 ===\n{step_content}")
                    else:
                        api_client.log(f"⚠️ 找不到步骤 {step_id} 的结果")
                
                content = "\n\n".join(combined_content)
                api_client.log(f"🔗 LLM数据来源: 步骤{source_step} (多步骤合并)")
            else:
                # 原有的单步骤逻辑
                if source_step not in step_results:
                    api_client.log(f"❌ 找不到步骤 {source_step} 的结果")
                    return False, None
                step_result = step_results[source_step]
                # keyboard → clipboard_content, drag → selected_text, rec_rec → recognized_text, get_data → data
                content = (step_result.get('clipboard_content') or 
                          step_result.get('selected_text') or 
                          step_result.get('recognized_text') or
                          step_result.get('data') or '')
                
                # 如果获取到的是字典格式的数据，需要转换为字符串
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                
                api_client.log(f"🔗 LLM数据来源: 步骤{source_step}")
        
            # 注意：此处无需再次从 step_result 读取内容，
            # 上方已在单步/多步分支内完成 content 的构建与类型转换。
        
        if not content:
            api_client.log("❌ 没有待处理的内容")
            return False, None
        
        # 获取prompt_name参数
        prompt_name = params.get('prompt_name')
        
        api_client.log(f"📝 准备LLM处理内容: {content[:50]}...")
        api_client.log(f"📊 LLM输入内容长度: {len(content)} 字符")
        
        # 显示更多调试信息
        if params.get('use_previous_result') and params.get('source_step'):
            source_step = params.get('source_step')
            # 这里根据 source_step 的类型分别打印调试信息，避免在列表上做 dict 成员测试引发 TypeError
            if isinstance(source_step, (list, tuple)):
                api_client.log(f"🔗 LLM数据来源: 步骤{source_step} (多步骤)")
                for sid in source_step:
                    if sid in step_results and isinstance(step_results[sid], dict):
                        api_client.log(f"🔍 源步骤{sid}结果键: {list(step_results[sid].keys())}")
                    else:
                        api_client.log(f"⚠️ 源步骤{sid}结果缺失或非字典")
            else:
                api_client.log(f"🔗 LLM数据来源: 步骤{source_step}")
                # 防御式：某些情况下 source_step 可能是不可哈希类型，避免抛出 TypeError
                try:
                    if source_step in step_results:
                        source_result = step_results[source_step]
                        api_client.log(f"🔍 源步骤结果键: {list(source_result.keys()) if isinstance(source_result, dict) else 'non_dict'}")
                except TypeError:
                    api_client.log("⚠️ source_step 类型不可哈希，已跳过字典成员检测")
        
        if prompt_name:
            api_client.log(f"🎯 使用prompt模板: {prompt_name}")
        
        # 调用服务器端LLM处理API
        payload = {
            "content": content
        }
        
        # 如果有prompt_name，添加到payload中
        if prompt_name:
            payload["prompt_name"] = prompt_name
        
        success, data = api_client.call_api("/api/llm/process", payload, timeout=600)
        
        if success:
            processed_result = data.get('processed_result', '')
            execution_time = data.get('execution_time', 0)
            
            api_client.log(f"✅ LLM处理完成 (耗时: {execution_time:.2f}秒)")
            api_client.log(f"📊 处理结果: {processed_result}")
            
            return True, {
                "processed_result": processed_result,
                "original_content": content,
                "execution_time": execution_time
            }
        else:
            api_client.log("❌ LLM处理失败")
            return False, None
            
    except Exception as e:
        error_msg = f"❌ LLM处理步骤异常: {str(e)}"
        if api_client:
            api_client.log(error_msg)
        elif log_callback:
            log_callback(error_msg)
        return False, None


def process_content_with_llm(
    content: str,
    api_client,
    timeout: int = 60
) -> Optional[str]:
    """
    直接处理内容的便捷函数
    
    Args:
        content: 待处理的内容
        api_client: API客户端实例
        timeout: 超时时间
    
    Returns:
        str | None: 处理后的结果，如果失败返回None
    """
    try:
        api_client.log(f"🔄 开始LLM处理: {content[:100]}...")
        
        payload = {"content": content}
        success, data = api_client.call_api("/api/llm/process", payload, timeout=timeout)
        
        if success:
            processed_result = data.get('processed_result', '')
            api_client.log(f"✅ LLM处理成功: {processed_result}")
            return processed_result
        else:
            api_client.log("❌ LLM处理失败")
            return None
            
    except Exception as e:
        api_client.log(f"❌ LLM处理异常: {str(e)}")
        return None


def batch_process_with_llm(
    contents: list,
    api_client,
    timeout: int = 600
) -> list:
    """
    批量处理多个内容
    
    Args:
        contents: 待处理的内容列表
        api_client: API客户端实例
        timeout: 每个请求的超时时间
    
    Returns:
        list: 处理结果列表
    """
    results = []
    
    for i, content in enumerate(contents):
        api_client.log(f"📋 批量处理 {i+1}/{len(contents)}")
        
        result = process_content_with_llm(content, api_client, timeout)
        results.append({
            "index": i,
            "original": content,
            "processed": result,
            "success": result is not None
        })
    
    success_count = sum(1 for r in results if r["success"])
    api_client.log(f"📊 批量处理完成: {success_count}/{len(contents)} 成功")
    
    return results


def validate_llm_result(result: str) -> bool:
    """
    验证LLM处理结果的格式
    
    Args:
        result: LLM处理结果
    
    Returns:
        bool: 是否符合预期格式
    """
    if not result:
        return False
    
    # 检查是否包含期望的字段
    expected_fields = ["账号名", "粉丝", "获赞"]
    found_fields = sum(1 for field in expected_fields if field in result)
    
    # 至少包含一半的期望字段
    return found_fields >= len(expected_fields) / 2


def extract_structured_data(result: str) -> Dict[str, str]:
    """
    从LLM结果中提取结构化数据
    
    Args:
        result: LLM处理结果
    
    Returns:
        dict: 结构化数据字典
    """
    import re
    
    data = {}
    
    # 提取各个字段
    patterns = {
        "account_name": r"账号名[：:]\s*([^，,]+)",
        "fans": r"粉丝[：:]\s*([^，,]+)",
        "likes": r"获赞[：:]\s*([^，,]+)",
        "identity": r"身份[：:]\s*([^，,]+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, result)
        if match:
            data[key] = match.group(1).strip()
    
    return data