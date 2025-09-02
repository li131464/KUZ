#!/usr/bin/env python3
"""
飞书写入操作模块
负责将上一步 LLM 的 processed_result 发送给服务端，由服务端异步写入飞书多维表格
"""

from typing import Optional, Dict, Any
import json


def execute_feishu_write(
    params: Dict[str, Any],
    step_results: Dict[int, Any],
    api_client,
    log_callback: Optional[callable] = None
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    执行飞书写入步骤
    - 优先从 source_step 的结果中读取 processed_result（严格JSON字符串）
    - 也支持 params 内直接提供 fields（dict）
    - 调用 /api/feishu/write 后立即返回，不阻塞流程
    """
    try:
        # 读取来源步骤
        processed_json_str = None
        if params.get('use_previous_result'):
            source_step = params.get('source_step')
            if source_step not in step_results:
                api_client.log(f"❌ 找不到步骤 {source_step} 的结果，无法写入飞书")
                return False, None
            prev = step_results[source_step] or {}
            processed_json_str = prev.get('processed_result')

        # 允许直接传 fields
        fields = params.get('fields')
        source = params.get('source')
        table_name = params.get('table_name')

        payload: Dict[str, Any] = {"source": source}
        
        # 如果有table_name，添加到payload中
        if table_name:
            payload["table_name"] = table_name
            api_client.log(f"🎯 目标表格: {table_name}")
        
        if fields:
            payload["fields"] = fields
        elif processed_json_str:
            payload["processed_result"] = processed_json_str
        else:
            api_client.log("❌ 未提供可写入飞书的数据（缺少 fields 或 processed_result）")
            return False, None

        api_client.log("🚀 提交飞书写入任务（异步）...")
        success, data = api_client.call_api("/api/feishu/write", payload, timeout=5)
        if not success:
            api_client.log("❌ 提交飞书写入任务失败")
            return False, None

        api_client.log("✅ 已提交飞书写入任务，服务端将后台处理")
        return True, {"submitted": True, "payload": payload}

    except Exception as e:
        if api_client:
            api_client.log(f"❌ 飞书写入步骤异常: {str(e)}")
        elif log_callback:
            log_callback(f"❌ 飞书写入步骤异常: {str(e)}")
        return False, None


