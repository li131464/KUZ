"""
更新对话框
显示更新信息和进度
"""

import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

# 尝试导入 qfluentwidgets
try:
    from qfluentwidgets import PrimaryPushButton, PushButton
    FLUENT_AVAILABLE = True
except ImportError:
    PrimaryPushButton = QPushButton
    PushButton = QPushButton
    FLUENT_AVAILABLE = False


class UpdateDialog(QDialog):
    """更新提示对话框"""
    
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setup_ui()
        self.load_changelog()
    
    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("发现新版本")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题区域
        self.create_header_section(layout)
        
        # 版本信息区域
        self.create_version_info_section(layout)
        
        # 更新日志区域
        self.create_changelog_section(layout)
        
        # 按钮区域
        self.create_button_section(layout)
        
        self.setLayout(layout)
        self.apply_styles()
    
    def create_header_section(self, layout):
        """创建标题区域"""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        # 主标题
        title = QLabel(f"🎉 发现新版本 {self.update_info['latest_version']}")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        
        # 副标题
        subtitle = QLabel("新版本已准备就绪，是否立即更新？")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_frame)
    
    def create_version_info_section(self, layout):
        """创建版本信息区域"""
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Box)
        info_layout = QVBoxLayout(info_frame)
        
        info_layout.addWidget(QLabel("📋 版本信息"))
        
        # 版本对比
        version_layout = QHBoxLayout()
        
        current_label = QLabel(f"当前版本: {self.update_info['current_version']}")
        current_label.setStyleSheet("color: #666;")
        
        arrow_label = QLabel("→")
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        
        new_label = QLabel(f"新版本: {self.update_info['latest_version']}")
        new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        version_layout.addWidget(current_label)
        version_layout.addWidget(arrow_label)
        version_layout.addWidget(new_label)
        version_layout.addStretch()
        
        info_layout.addLayout(version_layout)
        
        # 更新信息
        info_text = []
        info_text.append(f"📦 更新类型: {self.update_info.get('update_type', '未知').upper()}")
        info_text.append(f"📏 文件大小: {self.format_file_size(self.update_info.get('file_size', 0))}")
        info_text.append(f"📅 发布日期: {self.format_date(self.update_info.get('release_date', ''))}")
        
        if self.update_info.get('force_update', False):
            info_text.append("⚠️ 这是一个强制更新")
        
        info_label = QLabel("\n".join(info_text))
        info_label.setStyleSheet("font-size: 11px; color: #555;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_frame)
    
    def create_changelog_section(self, layout):
        """创建更新日志区域"""
        changelog_frame = QFrame()
        changelog_frame.setFrameStyle(QFrame.Box)
        changelog_layout = QVBoxLayout(changelog_frame)
        
        changelog_layout.addWidget(QLabel("📝 更新内容"))
        
        # 更新日志显示
        self.changelog_text = QTextEdit()
        self.changelog_text.setMaximumHeight(150)
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setPlaceholderText("正在加载更新日志...")
        
        changelog_layout.addWidget(self.changelog_text)
        layout.addWidget(changelog_frame)
    
    def create_button_section(self, layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        
        # 稍后提醒按钮
        if FLUENT_AVAILABLE:
            self.later_button = PushButton("稍后提醒")
        else:
            self.later_button = QPushButton("稍后提醒")
        self.later_button.clicked.connect(self.reject)
        
        # 跳过此版本按钮
        if FLUENT_AVAILABLE:
            self.skip_button = PushButton("跳过此版本")
        else:
            self.skip_button = QPushButton("跳过此版本")
        self.skip_button.clicked.connect(self.skip_version)
        
        # 立即更新按钮
        if FLUENT_AVAILABLE:
            self.update_button = PrimaryPushButton("立即更新")
        else:
            self.update_button = QPushButton("立即更新")
        self.update_button.clicked.connect(self.accept)
        
        # 如果是强制更新，只显示更新按钮
        if self.update_info.get('force_update', False):
            self.later_button.setVisible(False)
            self.skip_button.setVisible(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.later_button)
        button_layout.addWidget(self.skip_button)
        button_layout.addWidget(self.update_button)
        
        layout.addLayout(button_layout)
    
    def load_changelog(self):
        """加载更新日志"""
        try:
            # 这里应该从API获取更新日志，简化起见直接使用模拟数据
            version = self.update_info['latest_version']
            
            if version == "1.1.0":
                changelog = """
<h3>🚀 版本 1.1.0 新功能</h3>
<ul>
<li>➕ <b>新增计数器减法功能</b> - 现在可以点击-1按钮减少计数</li>
<li>ℹ️ <b>添加关于对话框</b> - 显示应用详细信息</li>
<li>🎨 <b>UI主题更新</b> - 从蓝色主题改为绿色主题</li>
</ul>

<h3>🔧 改进</h3>
<ul>
<li>⚡ 优化应用启动速度</li>
<li>🔄 改进更新检查机制</li>
<li>📱 更好的响应式布局</li>
</ul>

<h3>🐛 修复</h3>
<ul>
<li>修复计数器显示问题</li>
<li>修复更新检查偶尔失败的问题</li>
</ul>

<p><small>完全兼容 v1.0.0，支持无缝升级。</small></p>
                """
            else:
                changelog = f"<p>版本 {version} 的更新内容</p>"
            
            self.changelog_text.setHtml(changelog)
            
        except Exception as e:
            self.changelog_text.setPlainText(f"加载更新日志失败: {str(e)}")
    
    def skip_version(self):
        """跳过此版本"""
        reply = QMessageBox.question(
            self,
            "跳过版本",
            f"确定要跳过版本 {self.update_info['latest_version']} 吗？\n\n"
            "跳过后，此版本将不再提醒更新。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 这里可以记录跳过的版本
            self.done(2)  # 自定义返回码表示跳过
    
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "未知"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
    
    def format_date(self, date_str):
        """格式化日期"""
        try:
            from datetime import datetime
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            return date_str
        except:
            return date_str or "未知"
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            
            QFrame {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
            }
            
            QLabel {
                color: #333;
            }
            
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #5a6268;
            }
            
            QPushButton:pressed {
                background-color: #495057;
            }
            
            /* 主要按钮样式 */
            QPushButton[objectName="update_button"] {
                background-color: #28a745;
            }
            
            QPushButton[objectName="update_button"]:hover {
                background-color: #218838;
            }
            
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: #f8f9fa;
                font-size: 11px;
            }
        """)
        
        # 设置按钮对象名称以应用特定样式
        self.update_button.setObjectName("update_button")


class ProgressDialog(QDialog):
    """更新进度对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置进度对话框UI"""
        self.setWindowTitle("正在更新")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("🔄 正在更新应用")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        
        # 状态标签
        self.status_label = QLabel("准备下载...")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        # 详细信息
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("color: #666; font-size: 10px;")
        self.detail_label.setAlignment(Qt.AlignCenter)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.detail_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.apply_styles()
    
    def update_progress(self, percent, status, detail=""):
        """更新进度显示"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(status)
        self.detail_label.setText(detail)
        
        if percent >= 100:
            self.cancel_button.setText("关闭")
    
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
            
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
