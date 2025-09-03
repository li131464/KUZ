"""
在线更新测试项目 - 客户端主应用
基于 PyQt5 实现，模仿 0902_leo_client/app.py 的架构设计
"""

import sys
import os
import time
import json
from pathlib import Path

# PyQt5 imports - 与您的项目保持一致
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QDialog, QFrame, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon

# 尝试导入 qfluentwidgets（可选，与您的项目保持一致）
try:
    from qfluentwidgets import (
        PrimaryPushButton as FluentPrimaryButton,
        PushButton as FluentButton,
        Theme, setTheme
    )
    FLUENT_AVAILABLE = True
except ImportError:
    FluentPrimaryButton = QPushButton
    FluentButton = QPushButton
    def setTheme(*args, **kwargs):
        pass
    FLUENT_AVAILABLE = False

# 导入本地模块
from manipulate.api_client import APIClient
from manipulate.update_manager import UpdateManager


class UpdateCheckThread(QThread):
    """更新检查线程"""
    update_found = pyqtSignal(dict)
    check_completed = pyqtSignal(bool, str)
    
    def __init__(self, api_client, current_version):
        super().__init__()
        self.api_client = api_client
        self.current_version = current_version
    
    def run(self):
        """执行更新检查"""
        try:
            success, data = self.api_client.check_version(self.current_version)
            
            if success and isinstance(data, dict):
                if data.get("update_available", False):
                    self.update_found.emit(data)
                    self.check_completed.emit(True, "发现新版本")
                else:
                    self.check_completed.emit(True, "您已经是最新版本")
            else:
                error_msg = data.get("error", "检查更新失败") if isinstance(data, dict) else "检查更新失败"
                self.check_completed.emit(False, error_msg)
                
        except Exception as e:
            self.check_completed.emit(False, f"检查更新异常: {str(e)}")


class SimpleTestApp(QWidget):
    """简单的测试应用"""
    
    def __init__(self):
        super().__init__()
        self.current_version = self.load_current_version()
        self.counter = 0
        self.api_client = None
        self.update_manager = None
        self.update_check_thread = None
        
        self.init_api_client()
        self.init_ui()
        self.init_update_manager()
        
        # 启动时自动检查更新（延迟3秒）
        QTimer.singleShot(3000, self.auto_check_update)
    
    def load_current_version(self):
        """加载当前版本号"""
        version_file = Path(__file__).parent / "version.txt"
        try:
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                # 默认版本
                return "1.0.0"
        except Exception:
            return "1.0.0"
    
    def init_api_client(self):
        """初始化API客户端"""
        # 加载配置
        config_file = Path(__file__).parent / "config" / "update_config.json"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                base_url = config["update_server"]["base_url"]
        except Exception:
            base_url = "http://127.0.0.1:8000"
        
        self.api_client = APIClient(base_url, log_callback=self.log_message)
    
    def init_update_manager(self):
        """初始化更新管理器"""
        self.update_manager = UpdateManager(self.api_client, self.current_version, self.log_message)
        
        # 连接更新管理器信号
        self.update_manager.download_progress.connect(self.on_download_progress)
        self.update_manager.update_completed.connect(self.on_update_completed)
        self.update_manager.update_failed.connect(self.on_update_failed)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f'测试应用 v{self.current_version}')
        self.setGeometry(300, 300, 600, 500)
        
        # 设置应用图标（如果存在）
        try:
            icon_path = Path(__file__).parent / "public" / "logo.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题区域
        self.create_header_section(layout)
        
        # 功能区域
        self.create_function_section(layout)
        
        # 更新区域
        self.create_update_section(layout)
        
        # 日志区域
        self.create_log_section(layout)
        
        self.setLayout(layout)
        
        # 应用样式
        self.apply_theme()
    
    def create_header_section(self, layout):
        """创建标题区域"""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        # 应用标题
        title_label = QLabel("🚀 在线更新测试应用")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 版本信息
        self.version_label = QLabel(f"当前版本: v{self.current_version}")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("color: #666; font-size: 12px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.version_label)
        
        layout.addWidget(header_frame)
    
    def create_function_section(self, layout):
        """创建功能区域"""
        function_frame = QFrame()
        function_frame.setFrameStyle(QFrame.Box)
        function_layout = QVBoxLayout(function_frame)
        
        # 计数器显示
        self.counter_label = QLabel(f"计数器: {self.counter}")
        self.counter_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.counter_label.setAlignment(Qt.AlignCenter)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # +1 按钮
        if FLUENT_AVAILABLE:
            self.plus_button = FluentPrimaryButton("+1")
        else:
            self.plus_button = QPushButton("+1")
        self.plus_button.clicked.connect(self.increment_counter)
        
        # -1 按钮（v1.1.0 新功能）
        if self.current_version >= "1.1.0":
            if FLUENT_AVAILABLE:
                self.minus_button = FluentButton("-1")
            else:
                self.minus_button = QPushButton("-1")
            self.minus_button.clicked.connect(self.decrement_counter)
            button_layout.addWidget(self.minus_button)
        
        button_layout.addWidget(self.plus_button)
        
        # 关于按钮（v1.1.0 新功能）
        if self.current_version >= "1.1.0":
            if FLUENT_AVAILABLE:
                self.about_button = FluentButton("关于")
            else:
                self.about_button = QPushButton("关于")
            self.about_button.clicked.connect(self.show_about)
            button_layout.addWidget(self.about_button)
        
        function_layout.addWidget(QLabel("📊 应用功能演示"))
        function_layout.addWidget(self.counter_label)
        function_layout.addLayout(button_layout)
        
        layout.addWidget(function_frame)
    
    def create_update_section(self, layout):
        """创建更新区域"""
        update_frame = QFrame()
        update_frame.setFrameStyle(QFrame.Box)
        update_layout = QVBoxLayout(update_frame)
        
        update_layout.addWidget(QLabel("🔄 在线更新"))
        
        # 更新按钮
        button_layout = QHBoxLayout()
        
        if FLUENT_AVAILABLE:
            self.check_update_button = FluentPrimaryButton("检查更新")
        else:
            self.check_update_button = QPushButton("检查更新")
        self.check_update_button.clicked.connect(self.check_for_updates)
        
        # 更新状态
        self.update_status_label = QLabel("点击检查更新")
        self.update_status_label.setStyleSheet("color: #666;")
        
        button_layout.addWidget(self.check_update_button)
        button_layout.addStretch()
        button_layout.addWidget(self.update_status_label)
        
        update_layout.addLayout(button_layout)
        layout.addWidget(update_frame)
    
    def create_log_section(self, layout):
        """创建日志区域"""
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.Box)
        log_layout = QVBoxLayout(log_frame)
        
        log_layout.addWidget(QLabel("📝 系统日志"))
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("日志信息将在这里显示...")
        
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_frame)
    
    def apply_theme(self):
        """应用主题样式"""
        # 根据版本应用不同的主题颜色
        if self.current_version >= "1.1.0":
            # v1.1.0: 绿色主题
            theme_color = "#4CAF50"
            bg_color = "#f8fff8"
        else:
            # v1.0.0: 蓝色主题
            theme_color = "#2196F3"
            bg_color = "#f8f9ff"
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }}
            QFrame {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
                background-color: white;
            }}
            QPushButton {{
                background-color: {theme_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme_color}dd;
            }}
            QPushButton:pressed {{
                background-color: {theme_color}aa;
            }}
            QLabel {{
                color: #333;
            }}
            QTextEdit {{
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: #fafafa;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }}
        """)
    
    def increment_counter(self):
        """计数器+1"""
        self.counter += 1
        self.counter_label.setText(f"计数器: {self.counter}")
        self.log_message(f"计数器增加到: {self.counter}")
    
    def decrement_counter(self):
        """计数器-1 (v1.1.0新功能)"""
        self.counter -= 1
        self.counter_label.setText(f"计数器: {self.counter}")
        self.log_message(f"计数器减少到: {self.counter}")
    
    def show_about(self):
        """显示关于对话框 (v1.1.0新功能)"""
        QMessageBox.about(
            self,
            "关于",
            f"""
            <h3>在线更新测试应用</h3>
            <p><b>版本:</b> v{self.current_version}</p>
            <p><b>描述:</b> 演示在线更新功能的测试应用</p>
            <p><b>技术栈:</b> PyQt5 + FastAPI</p>
            <p><b>作者:</b> Claude AI</p>
            <hr>
            <p><small>这是一个用于测试在线更新功能的示例应用程序。</small></p>
            """
        )
    
    def auto_check_update(self):
        """自动检查更新"""
        self.log_message("🔍 启动时自动检查更新...")
        self.check_for_updates(silent=True)
    
    def check_for_updates(self, silent=False):
        """检查更新"""
        if self.update_check_thread and self.update_check_thread.isRunning():
            self.log_message("⚠️ 更新检查正在进行中...")
            return
        
        if not silent:
            self.log_message("🔍 手动检查更新...")
        
        self.check_update_button.setEnabled(False)
        self.update_status_label.setText("检查中...")
        
        # 创建检查线程
        self.update_check_thread = UpdateCheckThread(self.api_client, self.current_version)
        self.update_check_thread.update_found.connect(self.on_update_found)
        self.update_check_thread.check_completed.connect(self.on_check_completed)
        self.update_check_thread.start()
    
    def on_update_found(self, update_info):
        """发现更新"""
        self.log_message(f"✨ 发现新版本: {update_info['latest_version']}")
        
        # 显示更新对话框
        from manipulate.update_dialog import UpdateDialog
        dialog = UpdateDialog(update_info, self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.log_message("👍 用户确认更新，开始下载...")
            self.start_update(update_info)
        else:
            self.log_message("❌ 用户取消更新")
    
    def on_check_completed(self, success, message):
        """检查完成"""
        self.check_update_button.setEnabled(True)
        self.update_status_label.setText(message)
        
        if success:
            self.log_message(f"✅ 更新检查完成: {message}")
        else:
            self.log_message(f"❌ 更新检查失败: {message}")
    
    def start_update(self, update_info):
        """开始更新过程"""
        self.log_message("🚀 开始下载更新...")
        self.update_manager.start_update(update_info)
    
    def on_download_progress(self, percent, message):
        """下载进度更新"""
        self.update_status_label.setText(f"下载中... {percent}%")
        self.log_message(f"📥 {message}")
    
    def on_update_completed(self, success, message):
        """更新完成"""
        if success:
            self.log_message(f"🎉 更新完成: {message}")
            QMessageBox.information(self, "更新完成", "应用将重启以完成更新")
            self.restart_application()
        else:
            self.log_message(f"❌ 更新失败: {message}")
            QMessageBox.warning(self, "更新失败", f"更新过程中出现错误:\n{message}")
    
    def on_update_failed(self, error_message):
        """更新失败"""
        self.log_message(f"💥 更新异常: {error_message}")
        QMessageBox.critical(self, "更新异常", f"更新过程中发生异常:\n{error_message}")
    
    def restart_application(self):
        """重启应用程序"""
        self.log_message("🔄 准备重启应用...")
        
        # 关闭API客户端
        if self.api_client:
            self.api_client.close()
        
        # 重启应用
        import subprocess
        subprocess.Popen([sys.executable, __file__])
        QApplication.quit()
    
    def log_message(self, message):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted_message = f"[{timestamp}] {message}"
        
        # 添加到日志显示
        self.log_text.append(formatted_message)
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
        
        # 控制台输出
        print(formatted_message)
    
    def closeEvent(self, event):
        """应用关闭事件"""
        if self.api_client:
            self.api_client.close()
        
        if self.update_check_thread and self.update_check_thread.isRunning():
            self.update_check_thread.wait()
        
        event.accept()


def main():
    """主函数"""
    # 启用高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("在线更新测试应用")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TestOrg")
    
    # 创建并显示主窗口
    window = SimpleTestApp()
    window.show()
    
    # 启动事件循环
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
