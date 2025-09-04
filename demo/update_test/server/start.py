"""
在线更新测试项目 - 服务端 (PyInstaller版本)
基于 FastAPI 实现的更新服务器，支持exe文件的在线更新
模仿 0902_leo_server 的架构设计
"""

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional
import re

# 导入功能模块
from functions.version_manager import VersionManager
from functions.file_manager import FileManager

# 当前目录
current_dir = Path(__file__).parent

# 初始化 FastAPI 应用
app = FastAPI(
    title="更新服务器API",
    description="提供在线更新服务的API接口",
    version="1.0.0"
)

# 加载配置
def load_config():
    """加载服务端配置"""
    config_file = current_dir / "config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 默认配置
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8000
            },
            "versions": {
                "latest": "1.1.0",
                "supported": ["1.0.0", "1.1.0"],
                "force_update_from": "1.0.0"
            },
            "releases_path": "./releases"
        }

# 全局配置
CONFIG = load_config()

# 初始化管理器
version_manager = VersionManager(CONFIG)
file_manager = FileManager(CONFIG)

# Pydantic 模型
class VersionCheckRequest(BaseModel):
    """版本检查请求模型"""
    current_version: str
    platform: str
    arch: str

class VersionInfo(BaseModel):
    """版本信息响应模型"""
    current_version: str
    latest_version: str
    update_available: bool
    update_type: str
    force_update: bool
    download_url: str
    file_size: int
    changelog: str
    release_date: str

# ===================== API 端点 =====================

@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "在线更新服务器",
        "version": "1.0.0",
        "endpoints": [
            "/api/version/check",
            "/api/version/info/{version}",
            "/api/version/download/{version}",
            "/api/version/changelog/{version}"
        ],
        "supported_versions": CONFIG["versions"]["supported"],
        "latest_version": CONFIG["versions"]["latest"]
    }

@app.get("/api/version/check")
async def check_version(
    current_version: str = Query(..., description="当前版本号"),
    platform: str = Query(..., description="平台信息"),
    arch: str = Query(..., description="架构信息")
):
    """检查版本更新"""
    try:
        print(f"[版本检查] 当前版本: {current_version}, 平台: {platform}, 架构: {arch}")
        
        # 获取最新版本信息
        latest_version = CONFIG["versions"]["latest"]
        
        # 比较版本
        update_available = version_manager.compare_versions(current_version, latest_version) < 0
        
        if not update_available:
            return {
                "update_available": False,
                "current_version": current_version,
                "latest_version": latest_version,
                "message": "您已经是最新版本"
            }
        
        # 获取更新包信息
        package_info = file_manager.get_package_info(latest_version, platform, arch)
        
        if not package_info:
            raise HTTPException(status_code=404, detail="找不到对应的更新包")
        
        # 确定更新类型
        update_type = version_manager.get_update_type(current_version, latest_version)
        
        # 是否强制更新
        force_update = version_manager.is_force_update_required(current_version)
        
        return {
            "update_available": True,
            "current_version": current_version,
            "latest_version": latest_version,
            "update_type": update_type,
            "force_update": force_update,
            "download_url": f"/api/version/download_exe/{latest_version}",  # 下载exe文件
            "file_size": package_info["size"],
            "file_hash": package_info["hash"],
            "changelog": f"/api/version/changelog/{latest_version}",
            "release_date": package_info.get("release_date", "2024-09-03T10:00:00Z"),
            "message": f"发现新版本 {latest_version}",
            "update_mode": "pyinstaller_exe"  # 标识这是exe更新模式
        }
        
    except Exception as e:
        print(f"[错误] 版本检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"版本检查失败: {str(e)}")

@app.get("/api/version/info/{version}")
async def get_version_info(version: str):
    """获取指定版本的详细信息"""
    try:
        if version not in CONFIG["versions"]["supported"]:
            raise HTTPException(status_code=404, detail=f"不支持的版本: {version}")
        
        version_info = version_manager.get_version_details(version)
        return version_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本信息失败: {str(e)}")

@app.get("/api/version/download/{version}")
async def download_version(
    version: str,
    platform: str = Query("windows", description="平台信息"),
    arch: str = Query("x64", description="架构信息"),
    range_header: str = Header(None, alias="range")
):
    """下载指定版本的更新包（支持断点续传）"""
    try:
        if version not in CONFIG["versions"]["supported"]:
            raise HTTPException(status_code=404, detail=f"不支持的版本: {version}")
        
        # 获取文件路径
        package_path = file_manager.get_package_path(version, platform, arch)
        
        if not os.path.exists(package_path):
            raise HTTPException(status_code=404, detail="更新包文件不存在")
        
        file_size = os.path.getsize(package_path)
        
        # 处理 Range 请求（断点续传）
        if range_header:
            range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                
                print(f"[断点续传] 下载范围: {start}-{end}/{file_size}")
                
                def generate_chunk():
                    with open(package_path, 'rb') as f:
                        f.seek(start)
                        remaining = end - start + 1
                        while remaining > 0:
                            chunk_size = min(8192, remaining)
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                
                return StreamingResponse(
                    generate_chunk(),
                    status_code=206,
                    headers={
                        'Content-Range': f'bytes {start}-{end}/{file_size}',
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(end - start + 1),
                        'Content-Type': 'application/zip'
                    }
                )
        
        # 完整文件下载
        print(f"[完整下载] 文件: {package_path}, 大小: {file_size}")
        return FileResponse(
            package_path,
            media_type='application/zip',
            filename=f"update_v{version}_{platform}_{arch}.zip",
            headers={'Accept-Ranges': 'bytes'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[错误] 下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@app.get("/api/version/download_exe/{version}")
async def download_exe_version(
    version: str,
    range_header: str = Header(None, alias="range")
):
    """下载exe文件版本（PyInstaller专用，支持断点续传）"""
    try:
        print(f"[exe下载] 版本: {version}")
        
        if version not in CONFIG["versions"]["supported"]:
            raise HTTPException(status_code=404, detail=f"不支持的版本: {version}")
        
        # exe文件路径 - 假设exe文件存储在releases目录
        exe_filename = f"KuzflowApp_v{version}.exe"
        exe_path = current_dir / "releases" / f"v{version}" / exe_filename
        
        # 兼容旧的zip包结构（从zip包中提取exe）
        if not exe_path.exists():
            # 尝试从zip包中查找exe文件
            zip_path = current_dir / "releases" / f"v{version}" / f"update_v{version}.zip"
            if zip_path.exists():
                # 这里可以实现从zip中提取exe的逻辑
                # 为了演示，我们直接返回错误
                raise HTTPException(status_code=404, detail=f"exe文件不存在，只有zip包: {zip_path}")
        
        if not exe_path.exists():
            raise HTTPException(status_code=404, detail=f"exe文件不存在: {exe_path}")
        
        file_size = os.path.getsize(exe_path)
        print(f"[exe下载] 文件: {exe_path}, 大小: {file_size}")
        
        # 处理 Range 请求（断点续传）
        if range_header:
            range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                
                print(f"[断点续传] exe下载范围: {start}-{end}/{file_size}")
                
                def generate_chunk():
                    with open(exe_path, 'rb') as f:
                        f.seek(start)
                        remaining = end - start + 1
                        while remaining > 0:
                            chunk_size = min(8192, remaining)
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                
                return StreamingResponse(
                    generate_chunk(),
                    status_code=206,
                    headers={
                        'Content-Range': f'bytes {start}-{end}/{file_size}',
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(end - start + 1),
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'attachment; filename="{exe_filename}"'
                    }
                )
        
        # 完整文件下载
        print(f"[完整exe下载] 文件: {exe_path}, 大小: {file_size}")
        return FileResponse(
            exe_path,
            media_type='application/octet-stream',
            filename=exe_filename,
            headers={
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[错误] exe下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"exe下载失败: {str(e)}")

@app.get("/api/version/changelog/{version}")
async def get_changelog(version: str):
    """获取版本更新日志"""
    try:
        if version not in CONFIG["versions"]["supported"]:
            raise HTTPException(status_code=404, detail=f"不支持的版本: {version}")
        
        changelog = version_manager.get_changelog(version)
        return {"version": version, "changelog": changelog}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取更新日志失败: {str(e)}")

# ===================== 工具端点 =====================

@app.get("/api/debug/packages")
async def list_packages():
    """调试用：列出所有可用的更新包"""
    try:
        packages = file_manager.list_all_packages()
        return {"packages": packages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取包列表失败: {str(e)}")

@app.get("/api/debug/config")
async def get_config():
    """调试用：获取服务器配置"""
    return CONFIG

# ===================== 启动服务器 =====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 启动在线更新服务器")
    print(f"📍 服务地址: http://{CONFIG['server']['host']}:{CONFIG['server']['port']}")
    print(f"📦 支持版本: {', '.join(CONFIG['versions']['supported'])}")
    print(f"🆕 最新版本: {CONFIG['versions']['latest']}")
    print("=" * 60)
    
    uvicorn.run(
        "start:app",
        host=CONFIG["server"]["host"],
        port=CONFIG["server"]["port"],
        reload=True,
        log_level="info"
    )
