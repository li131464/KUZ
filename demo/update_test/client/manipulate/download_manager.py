"""
下载管理器
负责文件下载、断点续传等功能
"""

import os
import hashlib
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class DownloadThread(QThread):
    """下载线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态消息
    download_completed = pyqtSignal(str, str)  # 文件路径, 文件哈希
    download_failed = pyqtSignal(str)  # 错误消息
    
    def __init__(self, api_client, version, file_path, expected_size, expected_hash):
        super().__init__()
        self.api_client = api_client
        self.version = version
        self.file_path = file_path
        self.expected_size = expected_size
        self.expected_hash = expected_hash
        self.should_stop = False
    
    def run(self):
        """执行下载"""
        try:
            self.download_with_resume()
        except Exception as e:
            self.download_failed.emit(str(e))
    
    def download_with_resume(self):
        """支持断点续传的下载"""
        # 检查是否存在部分下载的文件
        resume_pos = 0
        if os.path.exists(self.file_path):
            resume_pos = os.path.getsize(self.file_path)
            self.progress_updated.emit(
                int((resume_pos / self.expected_size) * 100) if self.expected_size > 0 else 0,
                f"发现部分下载文件，从 {resume_pos} 字节处继续下载"
            )
        
        # 设置Range头进行断点续传
        range_header = f"bytes={resume_pos}-" if resume_pos > 0 else None
        
        # 开始下载
        success, response = self.api_client.download_version(
            self.version,
            range_header=range_header
        )
        
        if not success:
            raise Exception(f"下载请求失败: {response}")
        
        # 获取文件总大小
        if hasattr(response, 'headers'):
            content_range = response.headers.get('Content-Range')
            if content_range:
                # 解析 Content-Range: bytes 1024-2047/2048
                total_size = int(content_range.split('/')[-1])
            else:
                total_size = self.expected_size or int(response.headers.get('Content-Length', 0))
        else:
            total_size = self.expected_size
        
        # 打开文件进行写入
        mode = 'ab' if resume_pos > 0 else 'wb'
        downloaded = resume_pos
        
        start_time = time.time()
        last_update_time = start_time
        
        with open(self.file_path, mode) as f:
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.should_stop:
                        break
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新进度（每0.5秒更新一次）
                        current_time = time.time()
                        if current_time - last_update_time >= 0.5:
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                            else:
                                percent = 0
                            
                            # 计算下载速度
                            elapsed = current_time - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed / 1024 / 1024  # MB/s
                                eta = (total_size - downloaded) / (downloaded / elapsed) if downloaded > 0 else 0
                                status_msg = f"已下载 {downloaded}/{total_size} 字节 ({speed:.2f} MB/s, 剩余 {eta:.0f}s)"
                            else:
                                status_msg = f"已下载 {downloaded}/{total_size} 字节"
                            
                            self.progress_updated.emit(percent, status_msg)
                            last_update_time = current_time
                
                if self.should_stop:
                    self.download_failed.emit("下载被用户取消")
                    return
                
            except Exception as e:
                raise Exception(f"下载过程中出错: {str(e)}")
        
        # 验证文件完整性
        if total_size > 0 and downloaded != total_size:
            raise Exception(f"下载不完整: {downloaded}/{total_size} 字节")
        
        # 计算文件哈希
        file_hash = self.calculate_file_hash()
        
        # 验证哈希（如果提供了预期哈希）
        if self.expected_hash and file_hash != self.expected_hash:
            raise Exception("文件哈希校验失败")
        
        self.progress_updated.emit(100, f"下载完成: {downloaded} 字节")
        self.download_completed.emit(self.file_path, file_hash)
    
    def calculate_file_hash(self):
        """计算文件哈希"""
        sha256_hash = hashlib.sha256()
        try:
            with open(self.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def stop(self):
        """停止下载"""
        self.should_stop = True


class DownloadManager(QObject):
    """下载管理器"""
    
    # 信号定义
    download_progress = pyqtSignal(int, str)  # 进度百分比, 消息
    download_completed = pyqtSignal(str, str)  # 文件路径, 文件哈希
    download_failed = pyqtSignal(str)  # 错误消息
    
    def __init__(self, api_client, log_callback=None):
        super().__init__()
        self.api_client = api_client
        self.log_callback = log_callback
        self.download_thread = None
    
    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(f"[下载管理器] {message}")
        else:
            print(f"[下载管理器] {message}")
    
    def download_file(self, version, file_path, expected_size=0, expected_hash=""):
        """下载文件"""
        if self.download_thread and self.download_thread.isRunning():
            self.log("下载正在进行中...")
            return False
        
        try:
            self.log(f"开始下载版本 {version} 到 {file_path}")
            
            # 创建下载线程
            self.download_thread = DownloadThread(
                self.api_client,
                version,
                file_path,
                expected_size,
                expected_hash
            )
            
            # 连接信号
            self.download_thread.progress_updated.connect(self.on_progress_updated)
            self.download_thread.download_completed.connect(self.on_download_completed)
            self.download_thread.download_failed.connect(self.on_download_failed)
            
            # 启动下载
            self.download_thread.start()
            return True
            
        except Exception as e:
            self.log(f"启动下载失败: {e}")
            self.download_failed.emit(str(e))
            return False
    
    def cancel_download(self):
        """取消下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.log("取消下载...")
            self.download_thread.stop()
            self.download_thread.wait()
    
    def on_progress_updated(self, percent, message):
        """下载进度更新"""
        self.download_progress.emit(percent, message)
    
    def on_download_completed(self, file_path, file_hash):
        """下载完成"""
        self.log(f"下载完成: {file_path}")
        self.download_completed.emit(file_path, file_hash)
    
    def on_download_failed(self, error_message):
        """下载失败"""
        self.log(f"下载失败: {error_message}")
        self.download_failed.emit(error_message)
    
    def get_download_stats(self):
        """获取下载统计"""
        if self.download_thread and self.download_thread.isRunning():
            return {
                "is_downloading": True,
                "file_path": self.download_thread.file_path,
                "version": self.download_thread.version
            }
        else:
            return {
                "is_downloading": False
            }
