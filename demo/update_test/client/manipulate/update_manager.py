"""
更新管理器
负责协调整个更新过程
"""

import os
import json
import time
import shutil
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from .download_manager import DownloadManager
from .installer import UpdateInstaller


class UpdateManager(QObject):
    """更新管理器"""
    
    # 信号定义
    download_progress = pyqtSignal(int, str)  # 进度百分比, 消息
    update_completed = pyqtSignal(bool, str)  # 成功标志, 消息
    update_failed = pyqtSignal(str)  # 错误消息
    
    def __init__(self, api_client, current_version, log_callback=None):
        super().__init__()
        self.api_client = api_client
        self.current_version = current_version
        self.log_callback = log_callback
        
        # 初始化组件
        self.download_manager = DownloadManager(api_client, log_callback)
        self.installer = UpdateInstaller(log_callback)
        
        # 连接信号
        self.download_manager.download_progress.connect(self.on_download_progress)
        self.download_manager.download_completed.connect(self.on_download_completed)
        self.download_manager.download_failed.connect(self.on_download_failed)
        
        # 配置
        self.config = self.load_config()
        
        # 路径配置
        self.app_root = Path(__file__).parent.parent
        self.temp_dir = self.app_root / "temp"
        self.backup_dir = self.app_root / "backup"
        
        # 确保目录存在
        self.temp_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def load_config(self):
        """加载配置"""
        config_file = Path(__file__).parent.parent / "config" / "update_config.json"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"加载配置失败: {e}")
            return {
                "install_settings": {
                    "backup_enabled": True,
                    "auto_restart": True,
                    "rollback_on_failure": True
                }
            }
    
    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(f"[更新管理器] {message}")
        else:
            print(f"[更新管理器] {message}")
    
    def start_update(self, update_info):
        """开始更新过程"""
        try:
            self.log("开始更新过程...")
            self.update_info = update_info
            
            # 第一步：下载更新包
            self.download_update_package()
            
        except Exception as e:
            self.log(f"启动更新失败: {e}")
            self.update_failed.emit(str(e))
    
    def download_update_package(self):
        """下载更新包"""
        try:
            version = self.update_info["latest_version"]
            
            # 构建下载路径
            package_filename = f"update_v{version}.zip"
            download_path = self.temp_dir / package_filename
            
            self.log(f"开始下载更新包: {package_filename}")
            
            # 开始下载
            self.download_manager.download_file(
                version,
                str(download_path),
                self.update_info.get("file_size", 0),
                self.update_info.get("file_hash", "")
            )
            
        except Exception as e:
            self.log(f"下载更新包失败: {e}")
            self.update_failed.emit(str(e))
    
    def on_download_progress(self, percent, message):
        """下载进度更新"""
        self.download_progress.emit(percent, message)
    
    def on_download_completed(self, file_path, file_hash):
        """下载完成"""
        try:
            self.log(f"下载完成: {file_path}")
            
            # 验证文件完整性
            if self.update_info.get("file_hash") and file_hash:
                if file_hash != self.update_info["file_hash"]:
                    raise Exception("文件哈希校验失败")
                self.log("文件完整性验证通过")
            
            # 开始安装
            self.install_update(file_path)
            
        except Exception as e:
            self.log(f"下载完成处理失败: {e}")
            self.update_failed.emit(str(e))
    
    def on_download_failed(self, error_message):
        """下载失败"""
        self.log(f"下载失败: {error_message}")
        self.update_failed.emit(f"下载失败: {error_message}")
    
    def install_update(self, package_path):
        """安装更新"""
        try:
            self.log("开始安装更新...")
            
            # 创建备份（如果启用）
            if self.config.get("install_settings", {}).get("backup_enabled", True):
                self.create_backup()
            
            # 安装更新
            success = self.installer.install_update(
                package_path,
                str(self.app_root),
                self.current_version,
                self.update_info["latest_version"]
            )
            
            if success:
                self.log("更新安装成功")
                
                # 更新版本文件
                self.update_version_file(self.update_info["latest_version"])
                
                # 清理临时文件
                self.cleanup_temp_files()
                
                self.update_completed.emit(True, "更新安装成功")
            else:
                raise Exception("安装过程失败")
                
        except Exception as e:
            self.log(f"安装更新失败: {e}")
            
            # 尝试回滚（如果启用）
            if self.config.get("install_settings", {}).get("rollback_on_failure", True):
                self.rollback_update()
            
            self.update_failed.emit(str(e))
    
    def create_backup(self):
        """创建备份"""
        try:
            self.log("创建应用备份...")
            
            backup_name = f"backup_v{self.current_version}_{int(time.time())}"
            backup_path = self.backup_dir / backup_name
            
            # 备份关键文件
            files_to_backup = [
                "app.py",
                "manipulate/",
                "config/",
                "version.txt"
            ]
            
            backup_path.mkdir(exist_ok=True)
            
            for item in files_to_backup:
                source_path = self.app_root / item
                dest_path = backup_path / item
                
                if source_path.exists():
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
            
            self.backup_path = backup_path
            self.log(f"备份创建完成: {backup_path}")
            
        except Exception as e:
            self.log(f"创建备份失败: {e}")
            # 备份失败不应该阻止更新
    
    def rollback_update(self):
        """回滚更新"""
        try:
            if not hasattr(self, 'backup_path') or not self.backup_path.exists():
                self.log("没有可用的备份，无法回滚")
                return False
            
            self.log("开始回滚更新...")
            
            # 恢复备份文件
            for item in self.backup_path.iterdir():
                dest_path = self.app_root / item.name
                
                # 删除当前文件/目录
                if dest_path.exists():
                    if dest_path.is_dir():
                        shutil.rmtree(dest_path)
                    else:
                        dest_path.unlink()
                
                # 恢复备份
                if item.is_dir():
                    shutil.copytree(item, dest_path)
                else:
                    shutil.copy2(item, dest_path)
            
            self.log("回滚完成")
            return True
            
        except Exception as e:
            self.log(f"回滚失败: {e}")
            return False
    
    def update_version_file(self, new_version):
        """更新版本文件"""
        try:
            version_file = self.app_root / "version.txt"
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(new_version)
            self.log(f"版本文件已更新: {new_version}")
        except Exception as e:
            self.log(f"更新版本文件失败: {e}")
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            for file in self.temp_dir.glob("*.zip"):
                file.unlink()
                self.log(f"删除临时文件: {file.name}")
        except Exception as e:
            self.log(f"清理临时文件失败: {e}")
    
    def cleanup_old_backups(self, keep_count=3):
        """清理旧备份"""
        try:
            backups = sorted(
                [d for d in self.backup_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[keep_count:]:
                shutil.rmtree(old_backup)
                self.log(f"删除旧备份: {old_backup.name}")
                
        except Exception as e:
            self.log(f"清理旧备份失败: {e}")
