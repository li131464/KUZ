from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import requests
import base64
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
# 导入全部的工具函数
from functions.get_cordinate import get_cordinate
from functions.build_scroll_params import build_scroll_params
from functions.build_keyboard_operations import build_keyboard_operations
from functions.call_llm_service import call_llm_service
from functions.feishu import FeishuService
from functions.build_drag_params import build_drag_params
from functions.get_rec_xy import get_rec_xy
from functions.recognize_text import recognize_text_from_base64
# 添加OCR模块路径
current_dir = Path(__file__).parent
rec_dir = current_dir.parent.parent.parent / "rec"
sys.path.append(str(rec_dir))

# 导入自定义的OCR函数而不是直接导入PaddleOCR
import importlib.util
import json
import os as _os

def load_ocr_module():
    """动态加载OCR模块"""
    ocr_path = rec_dir / "ocr.py"
    spec = importlib.util.spec_from_file_location("ocr", ocr_path)
    ocr_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ocr_module)
    return ocr_module

# ===================== 配置加载器 =====================
def load_json_config(config_path: str) -> Dict[str, Any]:
    """加载JSON配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {config_path}, 错误: {e}")
        return {}

# ===================== 加载所有配置 =====================
configs_dir = current_dir / "configs"
# 多用户：用户配置根目录（仅按用户路径读取，不回退全局）
USERS_ROOT = current_dir / "users"

# 加载操作配置（坐标、滚动、键盘）
operation_config = load_json_config(configs_dir / "operation.json")
COORDINATE_DB = operation_config.get("coordinate_db", {})
SCROLL_DB = operation_config.get("scroll_db", {})
KEYBOARD_OPERATIONS_DB = operation_config.get("keyboard_operations_db", {})
DRAG_DB = operation_config.get("drag_db", {})
REC_DB = operation_config.get("rec_db", {})



# 加载 LLM 配置
llm_config = load_json_config(configs_dir / "llm.json")
LLM_PROMPT_DB = llm_config.get("llm_prompt_db", {})
# 新增：读取 llm 服务配置
LLM_SERVICE_CONFIG = llm_config.get("llm_service_config", {})

# 加载进程配置
process_config = load_json_config(configs_dir / "process.json")
PROCESS_DB = process_config.get("process_db", {})

# 加载飞书配置
feishu_config = load_json_config(configs_dir / "feishu.json")
credentials = feishu_config.get("credentials", {})
FEISHU_APP_ID = credentials.get("app_id", "")
FEISHU_APP_SECRET = credentials.get("app_secret", "")
FEISHU_APP_TOKEN = credentials.get("app_token", "")
FEISHU_TABLE_ID = credentials.get("table_id", "")
FEISHU_AUTH_URL = credentials.get("auth_url", "")
FEISHU_TABLE_DB = feishu_config.get("feishu_table_db", {})

# 新增：初始化 FeishuService
# 修改 FEISHU_SERVICE 的初始化
FEISHU_SERVICE = FeishuService(
    feishu_config.get("credentials", {}), 
    feishu_config.get("feishu_table_db", {}),
    feishu_config.get("feishu_doc_db", {})  # 添加文档配置
)
app = FastAPI(title="UI操作API服务", description="提供click、drag、scroll、rec等UI操作的坐标计算服务", version="1.0.0")

# ===================== 多用户：仅从 users/{user}/configs 读取 =====================
def _load_json_user_only(username: str, filename: str) -> Dict[str, Any]:
    """从 users/{user}/configs/{filename} 读取 JSON；不存在则返回空字典。
    - 参数:
      - username: 用户名
      - filename: 文件名（如 operation.json）
    - 返回: dict
    """
    try:
        user_path = USERS_ROOT / username / "configs" / filename
        if user_path.exists():
            with open(user_path, "r", encoding="utf-8") as f:
                return json.load(f)
        print(f"[多用户] 文件不存在: {user_path}")
        return {}
    except Exception as e:
        print(f"[多用户] 读取用户配置失败: {filename}, user={username}, 错误: {e}")
        return {}

def get_user_ctx(username: str) -> Dict[str, Any]:
    """组装当前用户的上下文字典 ctx（不缓存，MVP）。
    - 只读 users/{user}/configs 下的四个 JSON：operation.json / process.json / llm.json / feishu.json
    - 缺失则对应项为空字典
    """
    operation = _load_json_user_only(username, "operation.json")
    process   = _load_json_user_only(username, "process.json")
    llm       = _load_json_user_only(username, "llm.json")
    feishu    = _load_json_user_only(username, "feishu.json")

    ctx: Dict[str, Any] = {
        "COORDINATE_DB": operation.get("coordinate_db", {}),
        "SCROLL_DB": operation.get("scroll_db", {}),
        "KEYBOARD_OPERATIONS_DB": operation.get("keyboard_operations_db", {}),
        "DRAG_DB": operation.get("drag_db", {}),
        "REC_DB": operation.get("rec_db", {}),
        "PROCESS_DB": process.get("process_db", {}),
        "LLM_PROMPT_DB": llm.get("llm_prompt_db", {}),
        "LLM_SERVICE_CONFIG": llm.get("llm_service_config", {}),
        "FEISHU_CONFIG": feishu,
    }
    # 阶段打印，便于排查
    try:
        print(f"[多用户] ctx加载完成 user={username} keys={list(ctx.keys())}")
    except Exception:
        pass
    return ctx

def _get_feishu_service_for_user(username: str) -> FeishuService:
    """按用户构建 FeishuService（MVP：不缓存）。"""
    ctx = get_user_ctx(username)
    return FeishuService(
        ctx.get("FEISHU_CONFIG", {}).get("credentials", {}),
        ctx.get("FEISHU_CONFIG", {}).get("feishu_table_db", {}),
        ctx.get("FEISHU_CONFIG", {}).get("feishu_doc_db", {}),
    )

# Pydantic models
class ClickRequest(BaseModel):
    """点击请求模型"""
    operation: str
    step: int

class ClickXYRequest(BaseModel):
    """坐标点击请求模型"""
    target_description: str
    operation_id: Optional[str] = None


class ScrollRequest(BaseModel):
    """滚动请求模型"""
    scroll_description: str
    operation_id: Optional[str] = None

class RecRequest(BaseModel):
    """识别请求模型"""
    screenshot: str
    target_description: str
    operation_id: Optional[str] = None

class RecGetXYRequest(BaseModel):
    """获取识别目标坐标请求模型"""
    target_description: str
    operation_id: Optional[str] = None

class RecRecRequest(BaseModel):
    """截图识别请求模型"""
    screenshot: str
    target_description: str
    operation_id: Optional[str] = None

class GetProcessRequest(BaseModel):
    """获取流程配置请求模型"""
    task_name: str
    operation_id: Optional[str] = None

class LLMProcessRequest(BaseModel):
    """LLM处理请求模型"""
    content: Optional[str] = None
    prompt_name: Optional[str] = None
    operation_id: Optional[str] = None

class FeishuWriteRequest(BaseModel):
    """写入飞书请求模型"""
    fields: Optional[Dict[str, Any]] = None
    processed_result: Optional[str] = None
    source: Optional[str] = None
    table_name: Optional[str] = None

class KeyboardRequest(BaseModel):
    """键盘操作请求模型"""
    operation_name: Optional[str] = None
    operations: Optional[List[str]] = None
    operation_id: Optional[str] = None

class DragRequest(BaseModel):
    """拖拽请求模型"""
    target_description: str
    operation_id: Optional[str] = None

class ClickResponse(BaseModel):
    """点击响应模型"""
    success: bool
    coordinates: Tuple[int, int]
    confidence: float
    message: str = ""
    execution_time: float
    reference_match: Optional[Dict[str, Any]] = None

class DragResponse(BaseModel):
    """拖拽响应模型"""
    success: bool
    drag_params: Dict[str, Any]
    confidence: float
    message: str = ""
    execution_time: float

class ScrollResponse(BaseModel):
    """滚动响应模型"""
    success: bool
    scroll_params: Dict[str, Any]
    confidence: float
    message: str = ""
    execution_time: float

class RecResponse(BaseModel):
    """识别响应模型"""
    success: bool
    bounding_box: Dict[str, Tuple[int, int]]
    confidence: float
    message: str = ""
    execution_time: float

class KeyboardResponse(BaseModel):
    """键盘操作响应模型"""
    success: bool
    operation_name: str
    operations: List[str]
    has_clipboard_result: bool
    description: str
    execution_time: float
    message: str = ""

class ReferenceImageResponse(BaseModel):
    """参考图响应模型"""
    success: bool
    operation: str
    step: int
    images: List[Dict[str, Any]]
    message: str = ""

# ===================== API 端点 =====================
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "UI操作API服务",
        "version": "1.0.0",
        "endpoints": [
            "/api/click/xy",
            "/api/drag",
            "/api/scroll", 
            "/api/keyboard",
            "/api/feishu/write",
            "/api/llm/process",
            "/api/get_process",
            "/api/rec/get_xy",
            "/api/rec/rec"
        ]
    }

@app.post("/api/click/xy", response_model=ClickResponse)
async def click_by_coordinates(request: ClickXYRequest, x_user: str = Header(...)):
    try:
        ctx = get_user_ctx(x_user)
        success, coordinates, confidence, message, execution_time = get_cordinate(
            request.target_description, ctx["COORDINATE_DB"]
        )

        if not success:
            raise HTTPException(status_code=404, detail=message)

        return ClickResponse(
            success=True,
            coordinates=coordinates,
            confidence=confidence,
            message=message,
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}")

@app.post("/api/scroll", response_model=ScrollResponse)
async def get_scroll_params(request: ScrollRequest, x_user: str = Header(...)):
    try:
        ctx = get_user_ctx(x_user)
        success, scroll_params, message, execution_time, suggestions = build_scroll_params(
            request.scroll_description, ctx["SCROLL_DB"]
        )
        if not success:
            # 将相似匹配建议附加到 404 的提示文本中（保持 detail 为字符串，避免破坏兼容）
            raise HTTPException(status_code=404)

        return ScrollResponse(
            success=True,
            scroll_params=scroll_params,
            confidence=1.0,
            message=message,
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}")

# 恢复识别接口：/api/rec/get_xy
@app.post("/api/rec/get_xy")
async def get_recognition_coordinates(request: RecGetXYRequest, x_user: str = Header(...)):
    """
    获取识别目标的坐标（第一步）
    返回 {"upleft": [x, y], "downright": [x, y]}
    """
    import time
    start_time = time.time()

    try:
        ctx = get_user_ctx(x_user)
        success, upleft, downright, confidence, message, execution_time = get_rec_xy(
            request.target_description, ctx["REC_DB"]
        )
        if success:
            return {
                "upleft": upleft,
                "downright": downright
            }
        if not success:
            raise HTTPException(status_code=404, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}")

# 恢复识别接口：/api/rec/rec
@app.post("/api/rec/rec")
async def recognize_from_screenshot(request: RecRecRequest, x_user: str = Header(...)):
    """
    根据截图进行识别（第二步）
    返回字符串（识别文本），与备份文件保持一致
    """
    try:
        return recognize_text_from_base64(request.screenshot, request.target_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别错误: {str(e)}")

@app.post("/api/keyboard", response_model=KeyboardResponse)
async def get_keyboard_operations(request: KeyboardRequest, x_user: str = Header(...)):
    """根据请求返回键盘操作序列（优先使用传入的operations，忽略平台）"""
    import time
    start_time = time.time()
    
    try:
        ctx = get_user_ctx(x_user)
        success, payload, message, execution_time = build_keyboard_operations(
            request.operation_name,
            getattr(request, "operations", None),
            ctx["KEYBOARD_OPERATIONS_DB"],
        )
        if not success:
            raise HTTPException(status_code=404, detail=message)

        return KeyboardResponse(
            success=True,
            operation_name=payload["operation_name"],
            operations=payload["operations"],
            has_clipboard_result=payload["has_clipboard_result"],
            description=payload["description"],
            execution_time=execution_time,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}")

@app.post("/api/llm/process")
async def llm_process(request: LLMProcessRequest, x_user: str = Header(...)):
    try:
        # 统一交由 LLM Service 处理（含 prompt 构建、模型调用与回退）
        print(f"接收到LLM处理请求: content={(request.content or '')[:100]}..., prompt_name={request.prompt_name}")
        # 这里传入第三个参数：从 llm.json 读取的服务配置
        ctx = get_user_ctx(x_user)
        svc_res = call_llm_service(request.content, request.prompt_name, ctx["LLM_SERVICE_CONFIG"])

        # 直接将 service 的结果透传给客户端（仅保留接口需要的字段）
        return {
            "processed_result": svc_res.get("processed_result", ""),
            "execution_time": svc_res.get("execution_time", 0.0)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM处理错误: {str(e)}"
        )

@app.post("/api/feishu/write")
async def feishu_write(request: FeishuWriteRequest, background_tasks: BackgroundTasks, x_user: str = Header(...)):
    """客户端提交写入飞书的请求，服务端立即返回ok，并在后台执行写入"""
    try:
        # 统一交由“按用户构建”的 FeishuService 调度后台写入任务
        feishu_service = _get_feishu_service_for_user(x_user)
        return feishu_service.schedule_write(request, background_tasks)
    except Exception as e:
        print(f"/api/feishu/write 处理异常: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/drag")
async def get_drag_coordinates(request: DragRequest, x_user: str = Header(...)):
    """
    获取拖拽操作的起始和结束坐标
    返回结构与客户端期望一致：包含 start_position / end_position
    """
    try:
        ctx = get_user_ctx(x_user)
        success, start_position, end_position, message, execution_time, suggestions = build_drag_params(
            request.target_description, ctx["DRAG_DB"]
        )
        return {
            "start_position": start_position,
            "end_position": end_position,
            "target_description": request.target_description,
            "execution_time": execution_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取拖拽坐标错误: {str(e)}")

@app.post("/api/get_process")
async def get_process_config(request: GetProcessRequest, x_user: str = Header(...)):
    """获取流程配置"""
    try:
        ctx = get_user_ctx(x_user)
        if request.task_name not in ctx.get("PROCESS_DB", {}):
            available_tasks = list(ctx.get("PROCESS_DB", {}).keys())
            raise HTTPException(
                status_code=404,
                detail=f"未找到任务: {request.task_name}，可用任务: {available_tasks}"
            )
        
        process_config = ctx["PROCESS_DB"][request.task_name]

        # 返回扁平对象，并补充 total_steps，兼容客户端 executor 的使用
        steps = process_config.get("steps", [])
        return {**process_config, "total_steps": len(steps)}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"错误: {str(e)}")

# 在现有的请求模型后添加缺失的模型类
class GetDataRequest(BaseModel):
    """获取飞书数据请求模型"""
    source: str
    operation_id: Optional[str] = None

class WriteDocRequest(BaseModel):
    """写入飞书文档请求模型"""
    doc_name: str
    content: str
    operation_id: Optional[str] = None

class CheckCompleteRequest(BaseModel):
    """检查完成状态请求模型"""
    content: str  # 复制的页面内容
    target_keywords: List[str]  # 要检查的关键字列表
    click_position: Optional[str] = None  # 点击位置描述
    operation_id: Optional[str] = None

class CheckCompleteResponse(BaseModel):
    """检查完成状态响应模型"""
    success: bool
    keywords_found: bool  # 是否找到关键字
    found_keywords: List[str]  # 找到的关键字列表
    click_coordinates: Tuple[int, int]  # 浏览器准备复制的点击坐标
    message: str = ""
    execution_time: float

# 在API接口部分添加
@app.post("/api/check_complete", response_model=CheckCompleteResponse)
async def check_complete_status(request: CheckCompleteRequest, x_user: str = Header(...)):
    """检查页面加载完成状态"""
    import time
    start_time = time.time()
    
    try:
        content = request.content.lower()  # 转换为小写进行匹配
        target_keywords = [kw.lower() for kw in request.target_keywords]
        
        found_keywords = []
        for keyword in target_keywords:
            if keyword in content:
                found_keywords.append(keyword)
        
        keywords_found = len(found_keywords) > 0
        execution_time = time.time() - start_time
        
        # 从请求参数或默认配置获取点击坐标（按用户坐标库）
        ctx = get_user_ctx(x_user)
        if request.click_position:
            click_coordinates = ctx["COORDINATE_DB"].get(request.click_position, [1406, 177])
        else:
            click_coordinates = ctx["COORDINATE_DB"].get("点击浏览器准备复制", [1406, 177])
        
        return CheckCompleteResponse(
            success=True,
            keywords_found=keywords_found,
            found_keywords=found_keywords,
            click_coordinates=tuple(click_coordinates),
            message=f"检查完成，找到 {len(found_keywords)} 个关键字" if keywords_found else "未找到目标关键字",
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        # 异常情况下也返回默认坐标（按用户坐标库）
        ctx = get_user_ctx(x_user)
        if request.click_position:
            click_coordinates = ctx["COORDINATE_DB"].get(request.click_position, [1406, 177])
        else:
            click_coordinates = ctx["COORDINATE_DB"].get("点击浏览器准备复制", [1406, 177])
        
        return CheckCompleteResponse(
            success=False,
            keywords_found=False,
            found_keywords=[],
            click_coordinates=tuple(click_coordinates),
            message=f"检查异常: {str(e)}",
            execution_time=execution_time
        )

@app.post("/api/feishu/get_data")
async def get_feishu_data(request: GetDataRequest, x_user: str = Header(...)):
    """从飞书表格获取数据"""
    try:
        feishu_service = _get_feishu_service_for_user(x_user)
        result = feishu_service.get_data(request.source)
        if result["ok"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        print(f"/api/feishu/get_data 处理异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据错误: {str(e)}")

@app.post("/api/feishu/write_doc")
async def write_feishu_doc(request: WriteDocRequest, x_user: str = Header(...)):
    """向飞书文档写入内容"""
    try:
        feishu_service = _get_feishu_service_for_user(x_user)
        result = feishu_service.write_doc(request.doc_name, request.content)
        if result["ok"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        print(f"/api/feishu/write_doc 处理异常: {e}")
        raise HTTPException(status_code=500, detail=f"写入文档错误: {str(e)}")

# ===================== 登录与任务接口（多用户并发，无会话） =====================
class LoginRequest(BaseModel):
    user: str
    password: str

@app.post("/api/login")
async def api_login(req: LoginRequest):
    """使用 MySQL 校验用户与密码（dotenv 读取连接串）。成功即返回 ok，不创建会话。"""
    try:
        from dotenv import load_dotenv  # 延迟导入，避免全局依赖
        load_dotenv()
        import pymysql

        host = _os.getenv("MYSQL_HOST", "127.0.0.1")
        port = int(_os.getenv("MYSQL_PORT", "3306"))
        user = _os.getenv("MYSQL_USERNAME", "root")
        password = _os.getenv("MYSQL_PASSWORD", "")
        database = _os.getenv("MYSQL_DATABASE", "test")
        table = _os.getenv("MYSQL_TABLE_USER", "users")

        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset="utf8mb4")
        try:
            with conn.cursor() as cur:
                sql = f"SELECT 1 FROM `{table}` WHERE `user`=%s AND `password`=%s LIMIT 1"
                cur.execute(sql, (req.user, req.password))
                row = cur.fetchone()
                if row:
                    return {"ok": True, "user": req.user}
                else:
                    raise HTTPException(status_code=401, detail="用户名或密码错误")
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        # 为了新手易排查，返回清晰错误
        raise HTTPException(status_code=500, detail=f"登录异常: {str(e)}")

@app.get("/api/tasks")
async def api_tasks(x_user: str = Header(...)):
    """返回该用户可执行的任务列表（process.json 的键名）。"""
    try:
        ctx = get_user_ctx(x_user)
        tasks = list(ctx.get("PROCESS_DB", {}).keys())
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表异常: {str(e)}")
        if result["ok"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        print(f"/api/feishu/write_doc 处理异常: {e}")
        raise HTTPException(status_code=500, detail=f"写入文档错误: {str(e)}")

if __name__ == "__main__":
    # 启动说明：
    # - reload=True 开启自动重载
    # - reload_dirs 指定仅监听当前 server 目录及其子目录（避免无关目录触发重启）
    # - 这样在此目录下的代码调整都会触发自动重启，不必手动重启
    print(f"[启动] 使用自动重载，监听目录: {current_dir}")
    uvicorn.run(
        "start:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(current_dir)],  # 仅监听 server 目录及子目录
        log_level="info"
    )