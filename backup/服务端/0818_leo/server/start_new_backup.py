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

def load_ocr_module():
    """动态加载OCR模块"""
    ocr_path = rec_dir / "ocr.py"
    spec = importlib.util.spec_from_file_location("ocr", ocr_path)
    ocr_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ocr_module)
    return ocr_module

app = FastAPI(title="UI操作API服务", description="提供click、drag、scroll、rec等UI操作的坐标计算服务", version="1.0.0")

# 获取当前文件所在目录
current_dir = Path(__file__).parent


import random
# 坐标存储数据库（实际项目中可以使用真实数据库）
COORDINATE_DB = {
    "确定按钮": (960, 540),
    "取消按钮": (860, 540),
    "红色按钮": (800, 400),
    "关闭按钮": (1200, 100),
    "开始按钮": (500, 300),
    "输入框": (136, 246),
    "浏览器搜索框": (181, 100),
    "测试点击": (332 ,165),
    "点击浏览器准备复制": (714 + random.randint(0, 5), 165 + random.randint(0, 5))
}

# 滚动参数数据库
SCROLL_DB = {
    "向下滚动3次": {"clicks": 3, "direction": "down", "scroll_distance": 3},
    "向上滚动5次": {"clicks": 5, "direction": "up", "scroll_distance": 3},
    "向下滚动到底": {"clicks": 10, "direction": "down", "scroll_distance": 5},
    "向左滚动": {"clicks": 3, "direction": "left", "scroll_distance": 3},
    "向右滚动": {"clicks": 3, "direction": "right", "scroll_distance": 3},
    "快速向下滚动": {"clicks": 8, "direction": "down", "scroll_distance": 5},
    "加载页面内容": {"clicks": 5, "direction": "down", "scroll_distance": 4, "description": "滚动加载页面完整内容"},
    "深度滚动加载": {"clicks": 8, "direction": "down", "scroll_distance": 6, "description": "深度滚动确保所有内容加载"}
}

# 任务流程配置数据库
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
                    "text": "www.baidu.com",
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
    },
    "抖音信息复制流程": {
        "task_name": "抖音信息复制流程",
        "description": "自动化复制抖音两个页面的信息并写入飞书表格",
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
                    "text": "https://creator.douyin.com/creator-micro/content/manage",
                    "press_enter": True
                }
            },
            {
                "step_id": 3,
                "step_type": "wait",
                "step_name": "等待页面加载",
                "params": {
                    "wait_time": 3
                }
            },
            {
                "step_id": 4,
                "step_type": "click",
                "step_name": "点击浏览器准备复制",
                "params": {
                    "target_description": "点击浏览器准备复制"
                }
            },
            {
                "step_id": 5,
                "step_type": "keyboard",
                "step_name": "全选并复制第一页面内容",
                "params": {
                    "operation_name": "全选并复制",
                    "operations": ["command+a", "wait:200", "command+c"]
                }
            },
            {
                "step_id": 6,
                "step_type": "llm_process",
                "step_name": "LLM处理第一页面信息",
                "params": {
                    "prompt_name": "处理创作者信息",
                    "use_previous_result": True,
                    "source_step": 5
                }
            },
            {
                "step_id": 7,
                "step_type": "feishu_write",
                "step_name": "写入飞书多维表格1",
                "params": {
                    "table_name": "抖音创作者信息1",
                    "use_previous_result": True,
                    "source_step": 6,
                    "source": "抖音信息复制流程"
                }
            }
        ]
    }
}

# ===================== LLM Prompt 配置 =====================
LLM_PROMPT_DB = {
    "处理创作者信息": """
你是一个结构化信息抽取器。请从以下抖音创作者后台作品管理页面的文本中，提取所有视频的信息。
要求：
1) 只输出严格JSON数组格式（不包含任何多余文字/注释/解释/换行）
2) 每个视频提取：视频名称、发布时间、播放量、点赞数、评论数、分享数
3) 数字保留原始格式，时间格式保持不变
4) 忽略私密视频和无数据的条目

待抽取文本：
{content}

只输出如下形式的JSON数组：
[{{"视频名称":"AI提升企业效率10-12倍 #热点 #ai企业赋能","发布时间":"2025年06月30日 11:00","播放量":"7419","点赞数":"29","评论数":"0","分享数":"3"}},{{"视频名称":"...","发布时间":"...","播放量":"...","点赞数":"...","评论数":"...","分享数":"..."}}]
""".strip(),
    "处理用户信息": """
你是一个结构化信息抽取器。请从以下文本中仅抽取两个字段：用户名称、粉丝数。
要求：
1) 只输出严格JSON字符串（不包含任何多余文字/注释/解释/换行），键名必须是："用户名称"、"粉丝数"。
2) 粉丝数保留原文单位（如"万/亿"）。
3) 无法确定时用空字符串。

待抽取文本：
{content}

只输出如下形式：{{"用户名称":"...","粉丝数":"..."}}
""".strip()
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

# ===================== 键盘操作配置 =====================
KEYBOARD_OPERATIONS_DB = {
    "全选并复制": {
        "operation_name": "全选并复制",
        "description": "选择全部内容并复制到剪贴板",
        "operations": ["command+a", "wait:200", "command+c"],
        "has_clipboard_result": True,
        "platform_variants": {
            "darwin": ["command+a", "wait:200", "command+c"],
            "win32": ["ctrl+a", "wait:200", "ctrl+c"],
            "linux": ["ctrl+a", "wait:200", "ctrl+c"]
        }
    },
    "切换标签页": {
        "operation_name": "切换标签页",
        "description": "切换到下一个浏览器标签页",
        "operations": ["command+option+right"],
        "has_clipboard_result": False,
        "platform_variants": {
            "darwin": ["command+option+right"],
            "win32": ["ctrl+tab"],
            "linux": ["ctrl+tab"]
        }
    },
    "粘贴": {
        "operation_name": "粘贴",
        "description": "从剪贴板粘贴内容",
        "operations": ["command+v"],
        "has_clipboard_result": False,
        "platform_variants": {
            "darwin": ["command+v"],
            "win32": ["ctrl+v"],
            "linux": ["ctrl+v"]
        }
    },
    "撤销": {
        "operation_name": "撤销",
        "description": "撤销上一步操作",
        "operations": ["command+z"],
        "has_clipboard_result": False,
        "platform_variants": {
            "darwin": ["command+z"],
            "win32": ["ctrl+z"],
            "linux": ["ctrl+z"]
        }
    },
    "保存": {
        "operation_name": "保存",
        "description": "保存当前文档",
        "operations": ["command+s"],
        "has_clipboard_result": False,
        "platform_variants": {
            "darwin": ["command+s"],
            "win32": ["ctrl+s"],
            "linux": ["ctrl+s"]
        }
    }
}

# ===================== 飞书表格配置 =====================
FEISHU_TABLE_DB = {
    "抖音创作者信息1": {
        "app_token": FEISHU_APP_TOKEN,  # 使用环境变量/默认值
        "table_id": FEISHU_TABLE_ID,    # 使用环境变量/默认值
        "description": "抖音创作者视频信息（多维表格）",
        "fields_mapping": {
            "视频名称": "视频名称",
            "发布时间": "发布时间",
            "播放量": "播放量",
            "点赞数": "点赞数",
            "评论数": "评论数",
            "分享数": "分享数"
        },
        "is_array_data": True  # LLM 输出数组，逐条写入
    },
    "默认表格": {
        "app_token": "HpTobHZqtaPib9sZWlEcH5FFnDe",
        "table_id": "tblHCLKViWRWRxjA",
        "description": "默认表格配置",
        "fields_mapping": {
            "用户名称": "用户名称",
            "粉丝数": "粉丝数"
        }
    }
}


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
    content: Optional[str] = None  # 待处理的内容（OCR结果）
    prompt_name: Optional[str] = None  # Prompt名称，从LLM_PROMPT_DB获取
    operation_id: Optional[str] = None
class FeishuWriteRequest(BaseModel):
    """写入飞书请求模型"""
    fields: Optional[Dict[str, Any]] = None  # 直接传入表格字段
    processed_result: Optional[str] = None   # LLM返回的严格JSON字符串
    source: Optional[str] = None             # 记录来源（流程名）
    table_name: Optional[str] = None         # 表格名称，从FEISHU_TABLE_DB获取配置


class KeyboardRequest(BaseModel):
    """键盘操作请求模型"""
    operation_name: str  # 操作名称，如"全选并复制"
    platform: Optional[str] = None  # 操作系统平台，如"darwin", "win32", "linux"
    operation_id: Optional[str] = None

class DragRequest(BaseModel):
    """拖拽请求模型"""
    target_description: str  # 目标描述，如"用户信息区域"
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

class KeyboardResponse(BaseModel):
    """键盘操作响应模型"""
    success: bool
    operation_name: str
    operations: List[str]  # 操作序列
    has_clipboard_result: bool  # 是否有剪贴板结果
    description: str
    platform_used: str
    execution_time: float
    message: str = ""

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
            "/api/keyboard": "POST - 键盘操作",
            "/api/rec/get_xy": "POST - 获取识别目标的坐标",
            "/api/rec/rec": "POST - 根据截图进行识别",
            "/api/get_process": "POST - 获取任务流程配置",
            "/reference-images": "POST - 获取参考图",
            "/config/steps": "GET - 查看步骤配置",
            "/images/available": "GET - 查看可用图片",
            "/api/llm/process": "POST - LLM处理(支持prompt_name)",
            "/api/feishu/write": "POST - 写入飞书(支持table_name)"
        },
        "operations": {
            "click": ["click_xy"],
            "drag": ["拖拽操作"],
            "scroll": ["滚动操作"], 
            "keyboard": ["键盘操作"],
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
            "direction": scroll_config["direction"],
            "scroll_distance": scroll_config.get("scroll_distance", 3),  # 滚动距离/幅度
            "description": scroll_config.get("description", "")  # 滚动描述
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
        request: 包含待处理内容和/或prompt名称的请求体
    
    Returns:
        处理后的结构化结果
    """
    import time
    start_time = time.time()
    
    try:
        # 参数验证
        if not request.content and not request.prompt_name:
            raise HTTPException(
                status_code=400,
                detail="必须提供 content 或 prompt_name 参数"
            )
        
        content = request.content or ""
        print(f"接收到LLM处理请求: content={content[:100]}..., prompt_name={request.prompt_name}")
        
        # 构建LLM处理的prompt
        try:
            # 根据prompt_name获取对应的prompt模板
            if request.prompt_name:
                if request.prompt_name not in LLM_PROMPT_DB:
                    available_prompts = list(LLM_PROMPT_DB.keys())
                    raise HTTPException(
                        status_code=404,
                        detail=f"未找到prompt: {request.prompt_name}。可用prompts: {available_prompts}"
                    )
                prompt_template = LLM_PROMPT_DB[request.prompt_name]
                prompt = prompt_template.format(content=content)
                print(f"使用prompt模板: {request.prompt_name}")
            else:
                # 向后兼容：使用默认的prompt
                prompt = f"""
你是一个结构化信息抽取器。请从以下文本中仅抽取两个字段：用户名称、粉丝数。
要求：
1) 只输出严格JSON字符串（不包含任何多余文字/注释/解释/换行），键名必须是："用户名称"、"粉丝数"。
2) 粉丝数保留原文单位（如"万/亿"）。
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

    # 如果内容包含视频列表，则解析为数组格式
    if "播放" in content and "点赞" in content and "评论" in content:
        # 模拟解析视频信息
        videos = []
        # 简单的mock逻辑，实际应该用正则表达式解析
        if "AI提升企业效率10-12倍" in content:
            videos.append({
                "视频名称": "AI提升企业效率10-12倍 #热点 #ai企业赋能 #ai流量获客引流 #AI #AI科技",
                "发布时间": "2025年06月30日 11:00",
                "播放量": "7419",
                "点赞数": "29", 
                "评论数": "0",
                "分享数": "3"
            })
        if "AI如何赋予生产领域" in content:
            videos.append({
                "视频名称": "AI如何赋予生产领域？ #AI #AI科技 #AI管理 #热点 #生产厂家",
                "发布时间": "2025年06月27日 11:00",
                "播放量": "3879",
                "点赞数": "136",
                "评论数": "0", 
                "分享数": "0"
            })
        return _json.dumps(videos, ensure_ascii=False)
    else:
        # 原有的用户信息解析逻辑
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


def _feishu_write_array_background(records: List[Dict[str, Any]], source: Optional[str] = None, table_name: Optional[str] = None) -> None:
    """
    处理数组数据的飞书写入后台任务，逐条写入记录
    """
    import threading
    import time
    
    try:
        print(f"开始处理数组数据写入: {len(records)} 条记录，表格: {table_name}")
        
        success_count = 0
        failed_count = 0
        
        # 为不同表格添加不同的延迟，避免冲突
        if table_name == "抖音创作者信息2":
            initial_delay = 1.0  # 第二个表格延迟1秒开始
        else:
            initial_delay = 0.0
        
        if initial_delay > 0:
            print(f"表格 {table_name} 延迟 {initial_delay} 秒开始写入")
            time.sleep(initial_delay)
        
        for i, record in enumerate(records):
            try:
                # 为每条记录添加表格和序号标识
                record_source = f"{source}_{table_name}_记录{i+1}"
                _feishu_write_background(record, record_source, table_name)
                success_count += 1
                print(f"✅ {table_name} 第 {i+1}/{len(records)} 条记录写入成功")
                
                # 避免API频率限制，不同表格使用不同间隔
                if table_name == "抖音创作者信息1":
                    time.sleep(0.6)
                else:
                    time.sleep(0.8)
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ {table_name} 第 {i+1} 条记录写入失败: {e}")
        
        print(f"📊 {table_name} 数组写入完成: 成功 {success_count}/{len(records)} 条，失败 {failed_count} 条")
    except Exception as e:
        print(f"❌ {table_name} 数组数据写入异常: {e}")


def _feishu_write_background(fields: Dict[str, Any], source: Optional[str] = None, table_name: Optional[str] = None) -> None:
    try:
        token = _get_tenant_access_token()
        if not token:
            print("未获取到tenant_access_token，放弃写入飞书")
            return

        # 解析表格配置（仅 Bitable）
        if table_name and table_name in FEISHU_TABLE_DB:
            table_config = FEISHU_TABLE_DB[table_name]
            app_token = table_config["app_token"]
            table_id = table_config.get("table_id", "")
            print(f"使用多维表格配置: {table_name} -> {table_id}")
        else:
            # 使用默认配置
            app_token = FEISHU_APP_TOKEN
            table_id = FEISHU_TABLE_ID
            if table_name:
                available_tables = list(FEISHU_TABLE_DB.keys())
                print(f"未找到表格配置: {table_name}，可用表格: {available_tables}，使用默认配置")

        record_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        # 仅保留配置字段并转为字符串，确保和列完全一致
        filtered_fields = fields
        if table_name and table_name in FEISHU_TABLE_DB:
            mapping_keys = FEISHU_TABLE_DB[table_name].get("fields_mapping", {}).keys()
            if mapping_keys:
                filtered_fields = {k: str(fields.get(k, "")) for k in mapping_keys}

        body = {"fields": filtered_fields}

        resp = requests.post(
            record_url,
            headers=headers,
            json=body,
            timeout=10,
        )
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        print(f"写入飞书表格返回: table={table_name}, status={resp.status_code}, data={data}")
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
                elif isinstance(parsed, list):
                    # 处理JSON数组数据，需要逐条写入
                    table_config = FEISHU_TABLE_DB.get(request.table_name, {})
                    if table_config.get("is_array_data", False):
                        # 异步处理数组数据
                        background_tasks.add_task(_feishu_write_array_background, parsed, request.source, request.table_name)
                        return {"ok": True, "message": f"已安排写入 {len(parsed)} 条记录"}
                    else:
                        # 如果不是数组表格，取第一条数据
                        fields = parsed[0] if parsed else {}
            except Exception as e:
                print(f"解析processed_result失败: {e}")
                fields = {}

        # 根据表格配置确定字段
        if request.table_name and request.table_name in FEISHU_TABLE_DB:
            table_config = FEISHU_TABLE_DB[request.table_name]
            fields_mapping = table_config["fields_mapping"]
            feishu_fields = {}
            for field_name in fields_mapping.keys():
                feishu_fields[field_name] = str(fields.get(field_name, ""))
        else:
            # 默认字段（保持向后兼容）
            feishu_fields = {
                "用户名称": str(fields.get("用户名称", "")),
                "粉丝数": str(fields.get("粉丝数", "")),
            }

        # 安排后台任务写入飞书
        background_tasks.add_task(_feishu_write_background, feishu_fields, request.source, request.table_name)

        return {"ok": True}
    except Exception as e:
        # 即使异常也保证不阻塞客户端
        print(f"/api/feishu/write 处理异常: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/api/keyboard", response_model=KeyboardResponse)
async def get_keyboard_operations(request: KeyboardRequest):
    """
    根据操作名称返回键盘操作序列
    
    Args:
        request: 包含操作名称和平台信息的请求体
    
    Returns:
        包含操作序列和相关信息的响应
    """
    import time
    import platform
    start_time = time.time()
    
    try:
        operation_name = request.operation_name
        current_platform = request.platform or platform.system().lower()
        
        # 平台标准化
        if current_platform == "windows":
            current_platform = "win32"
        elif current_platform == "macos":
            current_platform = "darwin"
        
        print(f"接收到键盘操作请求: {operation_name}, 平台: {current_platform}")
        
        # 从键盘操作数据库查找
        if operation_name not in KEYBOARD_OPERATIONS_DB:
            available_operations = list(KEYBOARD_OPERATIONS_DB.keys())
            raise HTTPException(
                status_code=404,
                detail=f"未找到操作: {operation_name}。可用操作: {available_operations}"
            )
        
        operation_config = KEYBOARD_OPERATIONS_DB[operation_name]
        
        # 根据平台选择对应的操作序列
        if current_platform in operation_config.get("platform_variants", {}):
            operations = operation_config["platform_variants"][current_platform]
            print(f"使用平台特定操作序列: {current_platform}")
        else:
            operations = operation_config["operations"]
            print(f"使用默认操作序列")
        
        execution_time = time.time() - start_time
        
        return KeyboardResponse(
            success=True,
            operation_name=operation_name,
            operations=operations,
            has_clipboard_result=operation_config.get("has_clipboard_result", False),
            description=operation_config["description"],
            platform_used=current_platform,
            execution_time=execution_time,
            message=f"操作: {operation_name}, 平台: {current_platform}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"获取键盘操作错误: {str(e)}"
        )


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
            start_position = [260, 243]
            end_position = [360, 243]
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
