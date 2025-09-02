"""
流程执行器 - 负责执行完整的自动化流程
"""

import json
import os
from datetime import datetime
from .api_client import APIClient
from .recognition import get_screenshot_coordinates, recognize_screenshot
from .input_operations import execute_click, execute_input
from .file_operations import execute_save_result
from .wait_operations import execute_wait
from .drag_operations import execute_drag
from .llm_operations import execute_llm_process
# 在导入部分添加
from .feishu_operations import execute_feishu_write, execute_get_data, execute_write_doc
from .keyboard_operations import execute_keyboard
from .scroll_operations import execute_scroll
from .check_complete_operations import execute_check_complete

# 全局变量存储当前任务的日志文件路径
_current_task_log_file = None
_current_task_start_time = None

def save_step_results(step_results, task_name, status="in_progress"):
    """
    保存step_results到本地文件，方便调试
    使用同一个文件进行增量更新，避免产生多个冗余文件
    
    Args:
        step_results: 步骤结果字典
        task_name: 任务名称
        status: 执行状态
    """
    global _current_task_log_file, _current_task_start_time
    
    try:
        # 确保目录存在
        debug_dir = "debug_logs"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # 如果是新任务或者文件不存在，创建新的日志文件
        if (_current_task_log_file is None or 
            not os.path.exists(_current_task_log_file) or
            status.startswith("step_1_")):
            
            _current_task_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"step_results_{task_name}_{_current_task_start_time}.json"
            _current_task_log_file = os.path.join(debug_dir, filename)
            print(f"📋 创建新的日志文件: {_current_task_log_file}")
        
        # 准备保存的数据
        debug_data = {
            "task_name": task_name,
            "start_timestamp": _current_task_start_time,
            "last_update": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "status": status,
            "total_steps": len(step_results),
            "step_results": {}
        }
        
        # 转换step_results为可序列化的格式
        for step_id, result in step_results.items():
            debug_data["step_results"][str(step_id)] = {
                "step_id": step_id,
                "result_type": type(result).__name__,
                "result_keys": list(result.keys()) if isinstance(result, dict) else "non_dict",
                "result_data": result
            }
        
        # 写入文件（覆盖更新）
        with open(_current_task_log_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 Step results updated: {_current_task_log_file} (状态: {status})")
        
        # 如果任务完成或失败，清空全局变量
        if status in ["completed", "failed"] or "failed" in status:
            _current_task_log_file = None
            _current_task_start_time = None
            print(f"📋 任务日志记录完成，文件路径已清空")
        
        return _current_task_log_file
        
    except Exception as e:
        print(f"❌ Failed to save step results: {e}")
        return None

# def execute_process(task_name, log_callback=None, server_url="https://121.4.65.242"):
def execute_process(task_name, log_callback=None, server_url="http://127.0.0.1:8000"):
    """
    执行完整的自动化流程
    
    Args:
        task_name: 任务名称
        log_callback: 日志回调函数
        server_url: 服务器URL
    
    Returns:
        bool: 执行是否成功
    """
    # 创建API客户端
    api_client = APIClient(server_url, log_callback)
    
    try:
        # 第1步：获取流程配置
        api_client.log("📋 获取任务流程配置...")
        process_config = api_client.get_process_config(task_name)
        if not process_config:
            api_client.log("❌ 获取流程配置失败，流程终止")
            return False
        
        api_client.log(f"✅ 获取配置成功: {process_config['task_name']}")
        api_client.log(f"📝 任务描述: {process_config['description']}")
        api_client.log(f"📊 共 {process_config['total_steps']} 个步骤")
        
        # 第2步：执行流程步骤
        step_results = {}  # 存储每步的结果，供后续步骤使用
        
        for step in process_config['steps']:
            step_id = step['step_id']
            step_type = step['step_type']
            step_name = step['step_name']
            params = step['params']
            
            api_client.log(f"⚡ 步骤{step_id}：{step_name} ({step_type})")
            
            # 根据步骤类型执行对应操作
            success, result = execute_step(step_type, params, step_results, api_client)
            
            if success:
                # 将步骤名一并存入结果，便于下游（如多步合并的 LLM）引用显示
                if isinstance(result, dict):
                    # 使用下划线前缀，避免与业务字段冲突
                    result = {**result, "_step_name": step_name}
                step_results[step_id] = result
                api_client.log(f"✅ 步骤{step_id}完成")
                
                # 每完成一个步骤就保存一次，方便调试
                save_step_results(step_results, task_name, f"step_{step_id}_completed")
                
                # 特别关注复制步骤，保存详细信息
                if step_type == "keyboard" and result and result.get("has_clipboard_result"):
                    clipboard_content = result.get("clipboard_content", "")
                    api_client.log(f"🔍 调试信息 - 步骤{step_id}复制内容长度: {len(clipboard_content)}")
                    api_client.log(f"🔍 调试信息 - 步骤{step_id}复制内容预览: {clipboard_content[:100]}...")

                if step_type == "keyboard2" and result and result.get("has_clipboard_result"):
                    clipboard_content = result.get("clipboard_content", "")
                    api_client.log(f"🔍 调试信息 - 步骤{step_id}复制内容长度: {len(clipboard_content)}")
                    api_client.log(f"🔍 调试信息 - 步骤{step_id}复制内容预览: {clipboard_content[:100]}...")
                    
            else:
                api_client.log(f"❌ 步骤{step_id}失败，流程终止")
                save_step_results(step_results, task_name, f"step_{step_id}_failed")
                return False
        
        api_client.log("=" * 50)
        api_client.log("🎉 自动化流程完成!")
        
        # 保存最终的step_results
        final_file = save_step_results(step_results, task_name, "completed")
        api_client.log(f"📁 Step results已保存到: {final_file}")
        
        # 显示统计信息
        stats = api_client.get_stats()
        api_client.log(f"📊 API统计: {stats['total_requests']} 次请求，总耗时 {stats['total_time']:.2f}秒")
        
        return True
        
    except Exception as e:
        api_client.log(f"💥 流程异常: {str(e)}")
        return False


def execute_step(step_type, params, step_results, api_client):
    """
    执行单个步骤
    
    Args:
        step_type: 步骤类型
        params: 步骤参数
        step_results: 前面步骤的结果
        api_client: API客户端
    
    Returns:
        (success, result): 成功标志和结果数据
    """
    try:
        if step_type == "rec_get_xy":
            return get_screenshot_coordinates(params, api_client)
        elif step_type == "rec_rec":
            return recognize_screenshot(params, step_results, api_client)
        elif step_type == "click":
            return execute_click(params, api_client)
        elif step_type == "input":
            return execute_input(params, step_results, api_client)
        elif step_type == "save_result":
            return execute_save_result(params, step_results, api_client, api_client.log)
        elif step_type == "wait":
            return execute_wait(params, step_results, api_client, api_client.log)
        elif step_type == "drag":
            return execute_drag(params, step_results, api_client, api_client.log)
        elif step_type == "llm_process":
            return execute_llm_process(params, step_results, api_client, api_client.log)
        elif step_type == "feishu_write":
            return execute_feishu_write(params, step_results, api_client, api_client.log)
        elif step_type == "get_data":
            return execute_get_data(params, step_results, api_client, api_client.log)
        elif step_type == "write_doc":
            return execute_write_doc(params, step_results, api_client, api_client.log)
        elif step_type == "keyboard":
            return execute_keyboard(params, step_results, api_client, api_client.log)
        elif step_type == "keyboard2":
            return execute_keyboard(params, step_results, api_client, api_client.log)
        elif step_type == "scroll":
            return execute_scroll(params, step_results, api_client, api_client.log)
        elif step_type == "check_complete":
            return execute_check_complete(params, step_results, api_client, api_client.log)
        else:
            api_client.log(f"未知步骤类型: {step_type}")
            return False, None
            
    except Exception as e:
        api_client.log(f"步骤执行异常: {str(e)}")
        return False, None