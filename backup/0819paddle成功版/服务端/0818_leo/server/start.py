from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import requests
import base64
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 添加OCR模块路径
current_dir = Path(__file__).parent
rec_dir = current_dir.parent.parent.parent / "rec"
sys.path.append(str(rec_dir))

# 导入自定义的OCR函数而不是直接导入PaddleOCR
import importlib.util
import json

# 导入OCR点击服务
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'functions'))
from ocr_click_service import ocr_click_service

def load_ocr_module():
    """动态加载OCR模块"""
    ocr_path = rec_dir / "ocr.py"
    spec = importlib.util.spec_from_file_location("ocr", ocr_path)
    ocr_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ocr_module)
    return ocr_module

def load_llm_module():
    """动态加载LLM模块"""
    llm_path = rec_dir / "llm.py"
    spec = importlib.util.spec_from_file_location("llm", llm_path)
    llm_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm_module)
    return llm_module

app = FastAPI(title="UI操作API服务", description="提供click、drag、scroll、rec等UI操作的坐标计算服务", version="1.0.0")

# 获取当前文件所在目录
current_dir = Path(__file__).parent

# 步骤配置：每个step对应的参考图列表（按顺序）
# STEP_CONFIG = {
#     1: ["cross", "error", "delete"],
#     2: ["error", "delete", "cross"]
# }

# # 图片文件名映射（可根据实际文件名调整）
# IMAGE_FILES = {
#     "cross": "cross.png",
#     "error": "error.png", 
#     "delete": "delete.png"
# }

# 坐标存储数据库（实际项目中可以使用真实数据库）
COORDINATE_DB = {
    "确定按钮": (960, 540),
    "取消按钮": (860, 540),
    "红色按钮": (800, 400),
    "关闭按钮": (1200, 100),
    "开始按钮": (500, 300),
    "输入框": (136, 246),
    "浏览器搜索框": (181, 100)
}

# 滚动参数数据库
SCROLL_DB = {
    "向下滚动3次": {"clicks": 3, "direction": "down"},
    "向上滚动5次": {"clicks": 5, "direction": "up"},
    "向下滚动到底": {"clicks": 10, "direction": "down"},
    "向左滚动": {"clicks": 3, "direction": "left"},
    "向右滚动": {"clicks": 3, "direction": "right"},
    "快速向下滚动": {"clicks": 8, "direction": "down"}
}

# 动态加载流程配置
def load_process_config():
    """从configs/process.json加载流程配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'configs', 'process.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return config_data.get('process_db', {})
    except Exception as e:
        print(f"加载流程配置失败: {e}")
        return {}

# 任务流程配置数据库 - 从文件加载
PROCESS_DB = load_process_config()

# 如果文件加载失败，使用备用硬编码配置
if not PROCESS_DB:
    PROCESS_DB = {
    "识别并输入流程": {
        "task_name": "识别并输入流程",
        "description": "识别界面文字并自动输入到指定位置",
        "steps": [
            {
                "step_id": 1,
                "step_type": "rec_get_xy",
                "step_name": "获取截图区域",
                "params": {
                    "target_description": "流程控制"
                }
            },
            {
                "step_id": 2,
                "step_type": "rec_rec",
                "step_name": "图像识别",
                "params": {
                    "target_description": "流程控制"
                }
            },
            {
                "step_id": 3,
                "step_type": "click",
                "step_name": "点击输入框",
                "params": {
                    "target_description": "输入框"
                }
            },
            {
                "step_id": 4,
                "step_type": "input",
                "step_name": "输入文字",
                "params": {
                    "use_previous_result": True,
                    "source_step": 2
                }
            }
        ]
    },
    "简单点击流程": {
        "task_name": "简单点击流程",
        "description": "获取坐标并点击",
        "steps": [
            {
                "step_id": 1,
                "step_type": "click",
                "step_name": "点击按钮",
                "params": {
                    "target_description": "确定按钮"
                }
            }
        ]
    },
    "抖音用户信息获取流程": {
        "task_name": "抖音用户信息获取流程",
        "description": "获取抖音用户页面信息并保存到本地文件",
        "steps": [
            {
                "step_id": 1,
                "step_type": "click",
                "step_name": "点击浏览器搜索框",
                "params": {
                    "target_description": "浏览器搜索框"
                }
            },
            {
                "step_id": 2,
                "step_type": "input",
                "step_name": "输入链接并回车",
                "params": {
                    "text": "https://www.douyin.com/user/MS4wLjABAAAAh7MdVA-UbMYLeO3_zhA_Z-Mrkh8cDwBCU_qQqucnrFE",
                    "press_enter": True
                }
            },
            {
                "step_id": 3,
                "step_type": "wait",
                "step_name": "等待页面加载",
                "params": {
                    "wait_time": 3.0,
                    "reason": "等待抖音页面加载完成"
                }
            },
            {
                "step_id": 4,
                "step_type": "rec_get_xy",
                "step_name": "获取用户信息截图区域",
                "params": {
                    "target_description": "抖音用户信息区域"
                }
            },
            {
                "step_id": 5,
                "step_type": "rec_rec",
                "step_name": "识别用户信息",
                "params": {
                    "target_description": "抖音用户信息区域"
                }
            },
            {
                "step_id": 6,
                "step_type": "llm_process",
                "step_name": "LLM处理用户信息",
                "params": {
                    "use_previous_result": True,
                    "source_step": 5
                }
            },
            {
                "step_id": 7,
                "step_type": "save_result",
                "step_name": "保存结果到文件",
                "params": {
                    "filename": "result.txt",
                    "use_previous_result": True,
                    "source_step": 6
                }
            },
            {
                "step_id": 8,
                "step_type": "feishu_write",
                "step_name": "写入飞书多维表格",
                "params": {
                    "use_previous_result": True,
                    "source_step": 6,
                    "source": "抖音用户信息获取流程"
                }
            }
        ]
    }
    ,
    "拖拽识别流程": {
        "task_name": "拖拽识别流程",
        "description": "通过拖拽选择复制文本并进行LLM处理，最终保存结果",
        "steps": [
            {
                "step_id": 1,
                "step_type": "click",
                "step_name": "点击浏览器搜索框",
                "params": {
                    "target_description": "浏览器搜索框"
                }
            },
            {
                "step_id": 2,
                "step_type": "input",
                "step_name": "输入链接并回车",
                "params": {
                    "text": "https://www.douyin.com/user/MS4wLjABAAAAh7MdVA-UbMYLeO3_zhA_Z-Mrkh8cDwBCU_qQqucnrFE",
                    "press_enter": True
                }
            },
            {
                "step_id": 3,
                "step_type": "wait",
                "step_name": "等待页面加载",
                "params": {
                    "wait_time": 3.0,
                    "reason": "等待抖音页面加载完成"
                }
            },
            {
                "step_id": 4,
                "step_type": "drag",
                "step_name": "拖拽选择并复制用户信息",
                "params": {
                    "target_description": "抖音用户信息区域"
                }
            },
            {
                "step_id": 5,
                "step_type": "llm_process",
                "step_name": "LLM处理用户信息",
                "params": {
                    "use_previous_result": True,
                    "source_step": 4
                }
            },
            {
                "step_id": 6,
                "step_type": "save_result",
                "step_name": "保存结果到文件",
                "params": {
                    "filename": "result.txt",
                    "use_previous_result": True,
                    "source_step": 5
                }
            },
            {
                "step_id": 7,
                "step_type": "feishu_write",
                "step_name": "写入飞书多维表格",
                "params": {
                    "use_previous_result": True,
                    "source_step": 5,
                    "source": "拖拽识别流程"
                }
            }
        ]
    }
}

# ===================== 飞书配置 =====================
FEISHU_APP_ID = os.getenv("APP_ID", "cli_a7f2a82b4ef41013")
FEISHU_APP_SECRET = os.getenv("APP_SECRET", "Lr4KLyrpVvOJYEFj7L0KkdxIgbsB76IC")
FEISHU_APP_TOKEN = os.getenv("APP_TOKEN", "HpTobHZqtaPib9sZWlEcH5FFnDe")
FEISHU_TABLE_ID = os.getenv("TABLE_ID", "tblHCLKViWRWRxjA")
FEISHU_AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_BITABLE_RECORD_URL = (
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
)


class ClickRequest(BaseModel):
    """点击请求模型"""
    operation: str
    step: int


# 新增的操作请求模型
class ClickXYRequest(BaseModel):
    """坐标点击请求模型"""
    target_description: str  # 目标描述，如"红色按钮"、"确定"
    operation_id: Optional[str] = None


class DragRequest(BaseModel):
    """拖拽请求模型"""
    drag_description: str  # 拖拽描述，如"拖拽文件到回收站"
    operation_id: Optional[str] = None

class ScrollRequest(BaseModel):
    """滚动请求模型"""
    scroll_description: str  # 滚动描述，如"向下滚动3次"
    operation_id: Optional[str] = None

class RecRequest(BaseModel):
    """识别请求模型"""
    screenshot: str
    target_description: str  # "按钮", "输入框"等
    operation_id: Optional[str] = None

class RecGetXYRequest(BaseModel):
    """获取识别目标坐标请求模型"""
    target_description: str  # 目标描述，如"按钮"、"输入框"等
    operation_id: Optional[str] = None

class RecRecRequest(BaseModel):
    """截图识别请求模型"""
    screenshot: str  # base64编码的截图
    target_description: str  # 目标描述，如"按钮"、"输入框"等
    operation_id: Optional[str] = None

class GetProcessRequest(BaseModel):
    """获取流程配置请求模型"""
    task_name: str  # 任务名称，如"识别并输入流程"
    operation_id: Optional[str] = None

class LLMProcessRequest(BaseModel):
    """LLM处理请求模型"""
    content: str  # 待处理的内容（OCR结果）
    operation_id: Optional[str] = None
class FeishuWriteRequest(BaseModel):
    """写入飞书请求模型"""
    fields: Optional[Dict[str, Any]] = None  # 直接传入表格字段
    processed_result: Optional[str] = None   # LLM返回的严格JSON字符串
    source: Optional[str] = None             # 记录来源（流程名）


class DragRequest(BaseModel):
    """拖拽请求模型"""
    target_description: str  # 目标描述，如"用户信息区域"
    operation_id: Optional[str] = None

class OCRClickRequest(BaseModel):
    """OCR点击请求模型"""
    target_text: str  # 要查找并点击的目标文字
    screenshot: str  # base64编码的截图
    min_similarity_threshold: Optional[float] = 0.3  # 最低相似度阈值
    operation_id: Optional[str] = None

# 新增的操作响应模型
class ClickResponse(BaseModel):
    """点击响应模型"""
    success: bool
    coordinates: Tuple[int, int]  # [x, y]
    confidence: float
    message: str = ""
    execution_time: float
    reference_match: Optional[Dict[str, Any]] = None

class DragResponse(BaseModel):
    """拖拽响应模型"""
    success: bool
    drag_params: Dict[str, Any]  # pyautogui.drag()需要的参数
    confidence: float
    message: str = ""
    execution_time: float

class ScrollResponse(BaseModel):
    """滚动响应模型"""
    success: bool
    scroll_params: Dict[str, Any]  # pyautogui.scroll()需要的参数
    confidence: float
    message: str = ""
    execution_time: float

class RecResponse(BaseModel):
    """识别响应模型"""
    success: bool
    bounding_box: Dict[str, Tuple[int, int]]  # {"top_left": [x, y], "bottom_right": [x, y]}
    confidence: float
    message: str = ""
    execution_time: float

class OCRClickResponse(BaseModel):
    """OCR点击响应模型"""
    success: bool
    coordinates: Optional[Tuple[int, int]]  # 点击坐标 [x, y]
    confidence: float
    message: str = ""
    execution_time: float
    target_text: str
    suggestions: Optional[List[str]] = None  # 相似匹配建议

class ReferenceImageResponse(BaseModel):
    """参考图响应模型"""
    success: bool
    operation: str
    step: int
    images: List[Dict[str, Any]]
    message: str = ""


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "UI操作API服务",
        "version": "1.0.0",
        "description": "提供click、drag、scroll、rec等UI操作的坐标计算服务",
        "endpoints": {
            "/": "API信息",
            "/api/click/xy": "POST - 根据描述返回存储的坐标",
            "/api/drag": "POST - 拖拽操作",
            "/api/scroll": "POST - 计算滚动参数",
            "/api/rec/get_xy": "POST - 获取识别目标的坐标",
            "/api/rec/rec": "POST - 根据截图进行识别",
            "/api/ocr/click": "POST - OCR识别并返回点击坐标",
            "/api/get_process": "POST - 获取任务流程配置",
            "/reference-images": "POST - 获取参考图",
            "/config/steps": "GET - 查看步骤配置",
            "/images/available": "GET - 查看可用图片",
            "/api/llm/process": "POST - LLM处理",
            "/api/feishu/write": "POST - 写入飞书"
        },
        "operations": {
            "click": ["click_xy"],
            "drag": ["拖拽操作"],
            "scroll": ["滚动操作"], 
            "rec": ["识别操作", "get_xy", "rec"],
            "process": ["get_process"]
        }
    }


@app.post("/reference-images", response_model=ReferenceImageResponse)
async def get_reference_images(request: ClickRequest):
    """
    获取参考图像的base64编码列表
    
    Args:
        request: 包含operation和step的请求体
    
    Returns:
        包含参考图base64编码列表的响应
    """
    try:
        # 检查操作类型
        if request.operation != "click":
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的操作类型: {request.operation}，当前只支持 'click'"
            )
        
        # 检查步骤配置
        if request.step not in STEP_CONFIG:
            available_steps = list(STEP_CONFIG.keys())
            raise HTTPException(
                status_code=400,
                detail=f"不支持的步骤: {request.step}，支持的步骤: {available_steps}"
            )
        
        # 获取当前步骤对应的图片列表
        image_names = STEP_CONFIG[request.step]
        images_data = []
        
        ref_dir = current_dir / "ref"
        
        for image_name in image_names:
            # 获取图片文件名
            if image_name not in IMAGE_FILES:
                raise HTTPException(
                    status_code=500,
                    detail=f"图片配置错误: 未找到 '{image_name}' 的文件映射"
                )
            
            filename = IMAGE_FILES[image_name]
            image_path = ref_dir / filename
            
            # 检查文件是否存在
            if not image_path.exists():
                # 如果文件不存在，返回错误信息但不中断整个请求
                images_data.append({
                    "name": image_name,
                    "filename": filename,
                    "base64": None,
                    "error": f"文件不存在: {filename}",
                    "file_size": 0,
                    "mime_type": None
                })
                continue
            
            try:
                # 读取图片文件并转换为base64
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                    base64_encoded = base64.b64encode(image_data).decode('utf-8')
                
                # 获取文件信息
                file_size = len(image_data)
                mime_type = f"image/{image_path.suffix[1:].lower()}"
                
                images_data.append({
                    "name": image_name,
                    "filename": filename,
                    "base64": base64_encoded,
                    "error": None,
                    "file_size": file_size,
                    "mime_type": mime_type
                })
                
            except Exception as e:
                images_data.append({
                    "name": image_name,
                    "filename": filename,
                    "base64": None,
                    "error": f"读取文件错误: {str(e)}",
                    "file_size": 0,
                    "mime_type": None
                })
        
        # 检查是否有成功加载的图片
        successful_images = [img for img in images_data if img["base64"] is not None]
        
        return ReferenceImageResponse(
            success=len(successful_images) > 0,
            operation=request.operation,
            step=request.step,
            images=images_data,
            message=f"成功加载 {len(successful_images)}/{len(images_data)} 张参考图"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时发生错误: {str(e)}")


# 新增的操作API端点

@app.post("/api/click/xy", response_model=ClickResponse)
async def click_by_coordinates(request: ClickXYRequest):
    """
    根据目标描述返回存储的坐标
    
    Args:
        request: 包含目标描述的请求体
    
    Returns:
        包含点击坐标和置信度的响应
    """
    import time
    start_time = time.time()
    
    try:
        # 从坐标数据库查找
        if request.target_description not in COORDINATE_DB:
            raise HTTPException(
                status_code=404,
                detail=f"未找到目标: {request.target_description}"
            )
        
        coordinates = COORDINATE_DB[request.target_description]
        confidence = 1.0  # 存储的坐标置信度为1.0
        
        execution_time = time.time() - start_time
        
        return ClickResponse(
            success=True,
            coordinates=coordinates,
            confidence=confidence,
            message=f"目标: {request.target_description}",
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500, 
            detail=f"错误: {str(e)}"
        )



@app.post("/api/scroll", response_model=ScrollResponse)
async def get_scroll_params(request: ScrollRequest):
    """
    根据滚动描述返回pyautogui.scroll()需要的参数
    
    Args:
        request: 包含滚动描述的请求体
    
    Returns:
        包含滚动参数的响应
    """
    import time
    start_time = time.time()
    
    try:
        # 从滚动数据库查找
        if request.scroll_description not in SCROLL_DB:
            raise HTTPException(
                status_code=404,
                detail=f"未找到滚动参数: {request.scroll_description}"
            )
        
        scroll_config = SCROLL_DB[request.scroll_description]
        
        # 构造pyautogui.scroll()需要的参数
        scroll_params = {
            "clicks": scroll_config["clicks"],
            "x": None,  # 可选，在当前鼠标位置滚动
            "y": None,  # 可选，在当前鼠标位置滚动
            "direction": scroll_config["direction"]
        }
        
        confidence = 1.0
        execution_time = time.time() - start_time
        
        return ScrollResponse(
            success=True,
            scroll_params=scroll_params,
            confidence=confidence,
            message=f"滚动: {request.scroll_description}",
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"错误: {str(e)}"
        )



@app.post("/api/rec/get_xy")
async def get_recognition_coordinates(request: RecGetXYRequest):
    """
    获取识别目标的坐标（第一步）
    
    Args:
        request: 包含目标描述的请求体
    
    Returns:
        包含目标坐标和置信度的响应
    """
    import time
    start_time = time.time()
    
    try:
        # 特殊处理"流程控制"，返回截图区域边界框
        if request.target_description == "流程控制":
            top_left = [274, 173]
            bottom_right = [413, 198]
            
            return {
                "upleft": top_left,
                "downright": bottom_right
            }
        
        # 特殊处理"抖音用户信息区域"，返回用户信息区域坐标
        if request.target_description == "抖音用户信息区域":
            top_left = [319, 193]
            bottom_right = [646, 279]
            
            return {
                "upleft": top_left,
                "downright": bottom_right
            }
        
        # 其他目标的默认处理
        return {
            "upleft": [100, 100],
            "downright": [200, 150]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"错误: {str(e)}"
        )


@app.post("/api/rec/rec")
async def recognize_from_screenshot(request: RecRecRequest):
    """
    根据截图进行识别（第二步）
    
    Args:
        request: 包含base64截图和目标描述的请求体
    
    Returns:
        包含识别结果和边界框的响应
    """
    import time
    start_time = time.time()
    
    try:
        # 处理接收到的base64截图
        print(f"接收到截图数据长度: {len(request.screenshot)} 字符")
        print(f"识别目标: {request.target_description}")
        
        # 保存截图到文件（用于调试验证）
        try:
            import base64
            from datetime import datetime
            
            # 解码base64数据
            screenshot_data = base64.b64decode(request.screenshot)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"received_screenshot_{timestamp}.png"
            
            # 保存到服务器目录
            with open(filename, "wb") as f:
                f.write(screenshot_data)
            
            print(f"截图已保存到: {filename}")
            
        except Exception as e:
            print(f"保存截图失败: {e}")
        
        # 使用自定义OCR模块进行图像识别
        try:
            # 动态加载OCR模块
            ocr_module = load_ocr_module()
            
            # 创建临时输出目录
            temp_output_dir = current_dir / "temp_ocr_output"
            if not temp_output_dir.exists():
                temp_output_dir.mkdir()
            
            # 使用ocr.py中的ocr_recognize函数
            ocr_module.ocr_recognize(filename, str(temp_output_dir))
            
            # 读取生成的JSON文件
            base_name = os.path.splitext(os.path.basename(filename))[0]
            json_file = temp_output_dir / f"{base_name}.json"
            
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    ocr_data = json.load(f)
                
                # 提取文字内容
                recognized_texts = []
                if isinstance(ocr_data, dict) and 'rec_texts' in ocr_data:
                    recognized_texts = ocr_data['rec_texts']
                elif isinstance(ocr_data, list):
                    for item in ocr_data:
                        if 'text' in item:
                            recognized_texts.append(item['text'])
                
                # 清理临时文件
                json_file.unlink()
                
                # 拼接结果
                final_text = '\n'.join(recognized_texts) if recognized_texts else "未识别到文字内容"
                print(f"OCR识别结果: {final_text}")
                return final_text
            else:
                return "OCR识别失败: 未生成识别结果文件"
            
        except Exception as ocr_error:
            print(f"OCR识别失败: {ocr_error}")
            # 如果OCR识别失败，返回错误信息
            return f"OCR识别失败: {str(ocr_error)}"
        
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"识别错误: {str(e)}"
        )


@app.post("/api/llm/process")
async def process_with_llm(request: LLMProcessRequest):
    """
    使用LLM处理OCR结果
    
    Args:
        request: 包含待处理内容的请求体
    
    Returns:
        处理后的结构化结果
    """
    import time
    start_time = time.time()
    
    try:
        content = request.content
        print(f"接收到LLM处理请求: {content[:100]}...")
        
        # 使用真正的LLM模块进行处理
        try:
            # 动态加载LLM模块
            llm_module = load_llm_module()
            
            # 构造提示词：强约束仅输出飞书所需JSON（无其他字符）
            prompt = f"""
你是一个结构化信息抽取器。请从以下文本中仅抽取两个字段：用户名称、粉丝数。
要求：
1) 只输出严格JSON字符串（不包含任何多余文字/注释/解释/换行），键名必须是："用户名称"、"粉丝数"。
2) 粉丝数保留原文单位（如“万/亿”）。
3) 无法确定时用空字符串。

待抽取文本：
{content}

只输出如下形式：{{"用户名称":"...","粉丝数":"..."}}
"""
            
            # 使用阿里云通义千问API进行处理
            print("正在调用通义千问LLM进行处理...")
            
            try:
                from openai import OpenAI
                
                client = OpenAI(
                    api_key="sk-0808fa5018754ac28df073b3500fa6e6",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                )
                
                completion = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant for extracting user information."},
                        {"role": "user", "content": prompt},
                    ],
                )
                
                processed_result = completion.choices[0].message.content
                print(f"通义千问返回: {processed_result}")
                
            except Exception as api_error:
                print(f"通义千问API调用失败: {api_error}")
                # 直接返回mock结果
                processed_result = process_user_info_mock(content)
                print(f"使用Mock结果: {processed_result}")
            
        except Exception as llm_error:
            print(f"LLM调用失败: {llm_error}")
            # 直接返回mock结果
            processed_result = process_user_info_mock(content)
            print(f"备用Mock结果: {processed_result}")
        
        execution_time = time.time() - start_time
        print(f"LLM处理完成，耗时: {execution_time:.3f}秒")
        
        # 直接返回模型（或Mock）输出，要求其自身即为严格JSON字符串
        return {
            "processed_result": processed_result,
            "execution_time": execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"LLM处理错误: {str(e)}"
        )


def process_user_info_mock(content: str) -> str:
    """
    模拟LLM处理用户信息
    TODO: 替换为实际的LLM API调用
    """
    # Mock：直接构造飞书所需JSON字符串
    import re, json as _json

    username = "GEM鄧紫棋" if ("GEM" in content or "鄧紫棋" in content or "邓紫棋" in content) else ""
    fans = ""
    m = re.search(r"粉丝[：:]\s*([\d.]+\s*[万亿]?)", content)
    if m:
        fans = m.group(1)
    mock = {"用户名称": username, "粉丝数": fans}
    return _json.dumps(mock, ensure_ascii=False)


# 删除归一化函数，完全依赖大模型按提示输出JSON


# ===================== 飞书写入接口（异步） =====================

def _get_tenant_access_token() -> Optional[str]:
    try:
        resp = requests.post(
            FEISHU_AUTH_URL,
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
            timeout=10,
        )
        data = resp.json() if resp is not None else {}
        if resp.status_code == 200 and data.get("code", 0) == 0:
            return data.get("tenant_access_token")
        print(f"获取tenant_access_token失败: status={resp.status_code}, data={data}")
    except Exception as e:
        print(f"获取tenant_access_token异常: {e}")
    return None


def _feishu_write_background(fields: Dict[str, Any], source: Optional[str] = None) -> None:
    try:
        token = _get_tenant_access_token()
        if not token:
            print("未获取到tenant_access_token，放弃写入飞书")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {"fields": fields}

        resp = requests.post(
            FEISHU_BITABLE_RECORD_URL,
            headers=headers,
            json=body,
            timeout=10,
        )
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        print(f"写入飞书返回: status={resp.status_code}, data={data}")
    except Exception as e:
        print(f"写入飞书后台任务异常: {e}")


@app.post("/api/feishu/write")
async def feishu_write(request: FeishuWriteRequest, background_tasks: BackgroundTasks):
    """
    客户端提交写入飞书的请求，服务端立即返回ok，并在后台执行写入。
    优先使用 fields；如无，则从 processed_result（严格JSON字符串）解析。
    """
    try:
        fields: Dict[str, Any] = request.fields or {}

        if not fields and request.processed_result:
            try:
                parsed = json.loads(request.processed_result)
                if isinstance(parsed, dict):
                    fields = parsed
            except Exception:
                fields = {}

        # 仅保留飞书表格所需字段
        feishu_fields = {
            "用户名称": str(fields.get("用户名称", "")),
            "粉丝数": str(fields.get("粉丝数", "")),
        }

        # 安排后台任务写入飞书
        background_tasks.add_task(_feishu_write_background, feishu_fields, request.source)

        return {"ok": True}
    except Exception as e:
        # 即使异常也保证不阻塞客户端
        print(f"/api/feishu/write 处理异常: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/api/drag")
async def get_drag_coordinates(request: DragRequest):
    """
    获取拖拽操作的起始和结束坐标
    
    Args:
        request: 包含目标描述的请求体
    
    Returns:
        包含起始和结束坐标的响应
    """
    import time
    start_time = time.time()
    
    try:
        target_description = request.target_description
        print(f"接收到拖拽坐标请求: {target_description}")
        
        # 根据目标描述返回预设的拖拽坐标
        if target_description == "抖音用户信息区域":
            # 起始位置 (330, 220), 结束位置 (628, 255)
            start_position = [330, 220]
            end_position = [628, 255]
        else:
            # 默认拖拽区域
            start_position = [100, 100]
            end_position = [300, 200]
        
        execution_time = time.time() - start_time
        print(f"拖拽坐标返回完成，耗时: {execution_time:.3f}秒")
        
        return {
            "start_position": start_position,
            "end_position": end_position,
            "target_description": target_description,
            "execution_time": execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"获取拖拽坐标错误: {str(e)}"
        )


@app.post("/api/ocr/click", response_model=OCRClickResponse)
async def ocr_click(request: OCRClickRequest):
    """
    使用OCR识别目标文字并返回点击坐标
    
    Args:
        request: 包含目标文字、截图和相似度阈值的请求体
    
    Returns:
        包含点击坐标和置信度的响应
    """
    import time
    start_time = time.time()
    
    try:
        print(f"接收到OCR点击请求: 目标文字='{request.target_text}', 截图长度={len(request.screenshot)}, 相似度阈值={request.min_similarity_threshold}")
        
        # 调用OCR点击服务
        result = ocr_click_service(
            target_text=request.target_text,
            screenshot_base64=request.screenshot,
            min_similarity_threshold=request.min_similarity_threshold or 0.3
        )
        
        execution_time = time.time() - start_time
        print(f"OCR点击处理完成，耗时: {execution_time:.3f}秒")
        
        return OCRClickResponse(
            success=result["success"],
            coordinates=result["coordinates"],
            confidence=result["confidence"],
            message=result["message"],
            execution_time=result["execution_time"],
            target_text=result["target_text"],
            suggestions=result.get("suggestions")
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"OCR点击处理异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR点击处理错误: {str(e)}"
        )


@app.get("/config/steps")
async def get_step_config():
    """获取步骤配置信息"""
    return {
        "success": True,
        "step_config": STEP_CONFIG,
        "image_files": IMAGE_FILES,
        "description": "每个步骤对应的参考图列表（按顺序）"
    }


@app.get("/images/available")
async def get_available_images():
    """获取可用的图片文件列表"""
    try:
        ref_dir = current_dir / "ref"
        if not ref_dir.exists():
            return {"available_images": [], "message": "ref目录不存在"}
        
        available_images = []
        missing_images = []
        
        for image_name, filename in IMAGE_FILES.items():
            image_path = ref_dir / filename
            if image_path.exists():
                file_size = image_path.stat().st_size
                available_images.append({
                    "name": image_name,
                    "filename": filename,
                    "size": file_size,
                    "path": str(image_path)
                })
            else:
                missing_images.append({
                    "name": image_name,
                    "filename": filename,
                    "expected_path": str(image_path)
                })
        
        return {
            "success": True,
            "available_images": available_images,
            "missing_images": missing_images,
            "total_expected": len(IMAGE_FILES),
            "total_available": len(available_images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片信息时发生错误: {str(e)}")


@app.post("/api/get_process")
async def get_process_config(request: GetProcessRequest):
    """
    获取任务流程配置
    
    Args:
        request: 包含任务名称的请求体
    
    Returns:
        包含完整流程配置的JSON响应
    """
    import time
    start_time = time.time()
    
    try:
        # 从流程配置数据库查找
        if request.task_name not in PROCESS_DB:
            # 返回可用的任务列表
            available_tasks = list(PROCESS_DB.keys())
            raise HTTPException(
                status_code=404,
                detail=f"未找到任务: {request.task_name}。可用任务: {available_tasks}"
            )
        
        process_config = PROCESS_DB[request.task_name]
        execution_time = time.time() - start_time
        
        # 添加执行时间到响应中
        response = {
            **process_config,
            "execution_time": execution_time,
            "total_steps": len(process_config["steps"]),
            "request_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"返回任务配置: {request.task_name}, 包含 {len(process_config['steps'])} 个步骤")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"获取流程配置错误: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "start:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
