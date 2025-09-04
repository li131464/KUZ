"""
文件管理器
负责更新包的文件操作、哈希计算等功能
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List


class FileManager:
    """文件管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.releases_path = Path(config["releases_path"])
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        if not self.releases_path.exists():
            self.releases_path.mkdir(parents=True, exist_ok=True)
            print(f"创建发布目录: {self.releases_path}")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件的SHA256哈希值"""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败: {e}")
            return ""
    
    def get_package_path(self, version: str, platform: str = "windows", arch: str = "x64") -> str:
        """获取更新包的完整路径"""
        # 简化：所有平台使用同一个包文件
        package_name = f"update_v{version}.zip"
        version_dir = self.releases_path / f"v{version}"
        return str(version_dir / package_name)
    
    def get_exe_path(self, version: str, platform: str = "windows", arch: str = "x64") -> str:
        """获取exe文件的完整路径"""
        exe_name = f"KuzflowApp_v{version}.exe"
        version_dir = self.releases_path / f"v{version}"
        return str(version_dir / exe_name)
    
    def get_package_info(self, version: str, platform: str = "windows", arch: str = "x64") -> Optional[Dict[str, Any]]:
        """获取更新包信息（优先返回exe文件信息）"""
        # 优先查找exe文件
        exe_path = self.get_exe_path(version, platform, arch)
        if os.path.exists(exe_path):
            try:
                file_size = os.path.getsize(exe_path)
                file_hash = self.calculate_file_hash(exe_path)
                
                return {
                    "path": exe_path,
                    "size": file_size,
                    "hash": file_hash,
                    "platform": platform,
                    "arch": arch,
                    "version": version,
                    "release_date": "2024-09-03T10:00:00Z",
                    "file_type": "exe"
                }
            except Exception as e:
                print(f"获取exe文件信息失败: {e}")
        
        # 回退到zip包
        package_path = self.get_package_path(version, platform, arch)
        if not os.path.exists(package_path):
            print(f"更新包不存在: {package_path}")
            return None
        
        try:
            file_size = os.path.getsize(package_path)
            file_hash = self.calculate_file_hash(package_path)
            
            return {
                "path": package_path,
                "size": file_size,
                "hash": file_hash,
                "platform": platform,
                "arch": arch,
                "version": version,
                "release_date": "2024-09-03T10:00:00Z",
                "file_type": "zip"
            }
        except Exception as e:
            print(f"获取包信息失败: {e}")
            return None
    
    def list_all_packages(self) -> List[Dict[str, Any]]:
        """列出所有可用的更新包"""
        packages = []
        
        try:
            for version_dir in self.releases_path.iterdir():
                if version_dir.is_dir() and version_dir.name.startswith('v'):
                    version = version_dir.name[1:]  # 移除 'v' 前缀
                    
                    for package_file in version_dir.glob("*.zip"):
                        package_info = {
                            "version": version,
                            "filename": package_file.name,
                            "path": str(package_file),
                            "size": package_file.stat().st_size,
                            "hash": self.calculate_file_hash(str(package_file))
                        }
                        packages.append(package_info)
            
            return packages
        except Exception as e:
            print(f"列出包文件失败: {e}")
            return []
    
    def create_manifest(self, version: str, package_info: Dict[str, Any]) -> bool:
        """创建版本清单文件"""
        try:
            version_dir = self.releases_path / f"v{version}"
            manifest_path = version_dir / "manifest.json"
            
            manifest_data = {
                "version": version,
                "package": {
                    "filename": os.path.basename(package_info["path"]),
                    "size": package_info["size"],
                    "hash": package_info["hash"],
                    "download_url": f"/api/version/download/{version}"
                },
                "metadata": {
                    "release_date": package_info.get("release_date", "2024-09-03T10:00:00Z"),
                    "platform": package_info.get("platform", "windows"),
                    "arch": package_info.get("arch", "x64")
                }
            }
            
            import json
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
            print(f"创建清单文件: {manifest_path}")
            return True
            
        except Exception as e:
            print(f"创建清单文件失败: {e}")
            return False
    
    def verify_package_integrity(self, package_path: str, expected_hash: str) -> bool:
        """验证包文件完整性"""
        if not os.path.exists(package_path):
            return False
        
        actual_hash = self.calculate_file_hash(package_path)
        return actual_hash == expected_hash
    
    def cleanup_old_packages(self, keep_versions: int = 3):
        """清理旧的更新包（保留最新的几个版本）"""
        try:
            version_dirs = []
            for version_dir in self.releases_path.iterdir():
                if version_dir.is_dir() and version_dir.name.startswith('v'):
                    version_dirs.append(version_dir)
            
            # 按版本号排序（简单字符串排序）
            version_dirs.sort(key=lambda x: x.name, reverse=True)
            
            # 删除多余的版本
            for old_dir in version_dirs[keep_versions:]:
                import shutil
                shutil.rmtree(old_dir)
                print(f"清理旧版本: {old_dir.name}")
                
        except Exception as e:
            print(f"清理旧包失败: {e}")
    
    def get_download_stats(self) -> Dict[str, Any]:
        """获取下载统计信息（模拟）"""
        return {
            "total_downloads": 1250,
            "today_downloads": 45,
            "popular_versions": {
                "1.1.0": 850,
                "1.0.0": 400
            },
            "bandwidth_used": "125.6 GB",
            "success_rate": 98.5
        }
