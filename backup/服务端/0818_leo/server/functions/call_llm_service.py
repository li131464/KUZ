from typing import Optional, Dict, Any
from pathlib import Path
import json
import os
import time

def _load_llm_prompt_db() -> Dict[str, str]:
    """从 configs/llm.json 加载 llm_prompt_db"""
    current_dir = Path(__file__).parent  # server/functions
    configs_dir = current_dir.parent / "configs"
    llm_path = configs_dir / "llm.json"
    if not llm_path.exists():
        return {}
    try:
        with open(llm_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("llm_prompt_db", {}) or {}
    except Exception:
        return {}

def _process_user_info_mock(_: str) -> str:
    """与现有 start.py 的 mock 对齐"""
    return '{"用户名称":"测试用户","粉丝数":"10.5万"}'

def call_llm_service(content: Optional[str], prompt_name: Optional[str], model_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一的 LLM Service：
    - 自行加载 llm.json 的 prompt 模板并构建 prompt
    - 调用 LLM（优先通义千问 DashScope 兼容 OpenAI，其次 OpenAI 兼容接口）
    - 失败或缺少 prompt 时回退到 mock
    - 返回 processed_result 与 execution_time，供上层直接返回

    Args:
        content: 待处理文本
        prompt_name: llm.json 中 llm_prompt_db 的键名
        model_config: 可选模型配置，覆盖环境变量，示例：
            { "provider": "qwen" | "openai", "api_key": "...", "base_url": "...", "model": "..." }

    Returns:
        {
            "processed_result": str,
            "execution_time": float,
            "success": bool,
            "message": str,
            "model_used": str,
            "prompt_name": str
        }
    """
    start_ts = time.time()
    model_used = ""
    message = ""
    try:
        content = content or ""
        prompt_db = _load_llm_prompt_db()

        # 构建 prompt
        prompt: Optional[str] = None
        if prompt_name:
            if prompt_name in prompt_db:
                try:
                    prompt_template = prompt_db[prompt_name]
                    prompt = prompt_template.format(content=content)
                except Exception as e:
                    message = f"prompt 模板格式化失败: {e}"
            else:
                message = f"未找到 prompt: {prompt_name}"
        else:
            message = "缺少 prompt_name"

        # 如无可用 prompt，直接走 Mock 回退
        if not prompt:
            processed_result = _process_user_info_mock(content)
            exec_time = time.time() - start_ts
            return {
                "processed_result": processed_result,
                "execution_time": exec_time,
                "success": False,
                "message": f"LLM 跳过调用，原因: {message or '无可用prompt'}，已使用Mock",
                "model_used": model_used,
                "prompt_name": prompt_name or ""
            }

        # 选择提供商与模型参数
        provider = ""
        api_key = ""
        base_url = ""
        model = ""

        if model_config:
            provider = (model_config.get("provider") or "").strip().lower()
            api_key = model_config.get("api_key") or ""
            base_url = (model_config.get("base_url") or "").rstrip("/")
            model = model_config.get("model") or ""
        else:
            # 优先通义千问（DashScope 兼容 OpenAI）
            qwen_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if qwen_key:
                provider = "qwen"
                api_key = qwen_key
                base_url = (os.getenv("QWEN_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
                model = os.getenv("QWEN_MODEL") or "qwen-plus"
            else:
                provider = "openai"
                api_key = os.getenv("OPENAI_API_KEY") or ""
                base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
                model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

        if not api_key:
            raise RuntimeError("未配置可用的 LLM API Key")

        # OpenAI 兼容 chat.completions 调用
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)

        messages = [
            {"role": "system", "content": "You are a helpful assistant for extracting user information."},
            {"role": "user", "content": prompt},
        ]
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        model_used = model
        processed_result = completion.choices[0].message.content if completion and completion.choices else ""

        if not processed_result:
            raise RuntimeError("LLM 返回空内容")

        exec_time = time.time() - start_ts
        return {
            "processed_result": processed_result,
            "execution_time": exec_time,
            "success": True,
            "message": "",
            "model_used": model_used,
            "prompt_name": prompt_name or ""
        }

    except Exception as e:
        # 全量回退到 Mock
        processed_result = _process_user_info_mock(content or "")
        exec_time = time.time() - start_ts
        return {
            "processed_result": processed_result,
            "execution_time": exec_time,
            "success": False,
            "message": f"LLM 服务调用失败: {e}，已使用Mock",
            "model_used": model_used,
            "prompt_name": prompt_name or ""
        }