import sys
import time
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QCheckBox, QSpinBox, QScrollArea, QDialog, QFrame, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QCoreApplication, QRectF, QVariantAnimation
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QBrush, QPen

# 导入manipulate模块
from manipulate import execute_process
from manipulate.api_client import APIClient

# 资源路径解析函数：兼容开发环境与 PyInstaller 打包运行环境
def resource_path(relative_path: str) -> str:
    """返回资源文件的绝对路径
    - 打包环境: 使用 sys._MEIPASS 指向的临时目录
    - 开发环境: 使用当前工作目录
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    from qfluentwidgets import (
        PrimaryPushButton as FluentPrimaryButton,
        PushButton as FluentButton,
        LineEdit as FluentLineEdit,
        Theme, setTheme, setThemeColor
    )
    FLUENT_AVAILABLE = True
except Exception:
    FluentPrimaryButton = QPushButton
    FluentButton = QPushButton
    class FluentLineEdit(QLineEdit):
        pass
    def setTheme(*args, **kwargs):
        pass
    def setThemeColor(*args, **kwargs):
        pass
    class Theme:
        AUTO = None
    FLUENT_AVAILABLE = False

class ProcessThread(QThread):
    """处理流程执行的线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, task_name, server_url, loop_count=1, loop_interval=0, enable_infinite_loop=False):
        super().__init__()
        self.task_name = task_name
        self.server_url = server_url
        self.loop_count = loop_count
        self.loop_interval = loop_interval
        self.enable_infinite_loop = enable_infinite_loop  # 新增参数
        self.should_stop = False
    
    def run(self):
        """执行流程"""
        try:
            group_number = 1
            
            # 根据是否启用无限循环来决定执行方式
            if self.enable_infinite_loop:
                # 无限循环模式
                while not self.should_stop:
                    self._execute_group(group_number)
                    if self.should_stop:
                        break
                    self._wait_between_groups()
                    group_number += 1
            else:
                # 单次执行模式
                self._execute_group(group_number)
                
            self.finished_signal.emit(True)
                
        except Exception as e:
            self.log_signal.emit(f"💥 流程异常: {str(e)}")
            self.finished_signal.emit(False)
    
    def _execute_group(self, group_number):
        """执行一组任务"""
        self.log_signal.emit(f"🔄 开始第 {group_number} 组运行 (每组 {self.loop_count} 次)")
        
        # 在一组内连续运行指定次数
        for i in range(self.loop_count):
            if self.should_stop:
                self.log_signal.emit("🛑 循环已被用户停止")
                return
                
            self.log_signal.emit(f"🚀 第 {group_number} 组 - 第 {i+1}/{self.loop_count} 次执行...")
            self.log_signal.emit("=" * 50)
            
            success = execute_process(
                task_name=self.task_name,
                log_callback=self.log_signal.emit,
                server_url=self.server_url
            )
            
            if success:
                self.log_signal.emit("=" * 50)
                self.log_signal.emit(f"✅ 第 {group_number} 组 - 第 {i+1} 次执行完成!")
            else:
                self.log_signal.emit("=" * 50)
                self.log_signal.emit(f"❌ 第 {group_number} 组 - 第 {i+1} 次执行失败!")
        
        self.log_signal.emit(f"🎉 第 {group_number} 组执行完成!")
    
    def _wait_between_groups(self):
        """组间等待"""
        if self.loop_interval > 0 and not self.should_stop:
            self.log_signal.emit(f"⏳ 等待 {self.loop_interval} 秒后开始下一组...")
            
            # 分秒倒计时
            for remaining in range(self.loop_interval, 0, -1):
                if self.should_stop:
                    self.log_signal.emit("🛑 循环已被用户停止")
                    return
                self.log_signal.emit(f"⏰ 剩余等待时间: {remaining} 秒")
                time.sleep(1)
    
    def stop(self):
        """停止执行"""
        self.should_stop = True

class ToggleSwitch(QWidget):
    """自定义开关组件（带滑动圆点），尺寸 44x22，颜色符合当前主题
    - checked: bool 状态
    - toggled(bool) 信号
    """
    toggled = pyqtSignal(bool)
    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self._checked = checked
        # 0.0 ~ 1.0 的动画偏移，用于圆点位置
        self._anim = QVariantAnimation(self, startValue=1.0 if checked else 0.0, endValue=1.0 if checked else 0.0)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self.update)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool):
        if self._checked == value:
            return
        self._checked = value
        self._anim.stop()
        self._anim.setStartValue(self._anim.currentValue() or (1.0 if not value else 0.0))
        self._anim.setEndValue(1.0 if value else 0.0)
        self._anim.start()
        self.toggled.emit(value)
        self.update()

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 轨道
        radius = 11
        rect = QRectF(1, 1, self.width()-2, self.height()-2)
        if self._checked:
            track_color = QColor("#01CBCB")
        else:
            track_color = QColor(223, 238, 238)
            track_color.setAlphaF(0.28)
        painter.setBrush(QBrush(track_color))
        painter.setPen(QPen(track_color))
        painter.drawRoundedRect(rect, radius, radius)

        # 圆点
        t = float(self._anim.currentValue() if self._anim.state() != 0 else (1.0 if self._checked else 0.0))
        knob_d = 18
        margin = (self.height() - knob_d) / 2
        x = margin + t * (self.width() - knob_d - 2*margin)
        knob_rect = QRectF(x, margin, knob_d, knob_d)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(knob_rect)

class SimpleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.process_thread = None
        # 标记登录是否成功（用于启动阶段决定是否展示主窗口）
        self.login_ok = False
        self.init_ui()
        # 启动后显示登录对话框，登录成功再加载任务（多用户：X-User）
        try:
            self.show_login_dialog_and_load()
        except Exception as e:
            print(f"[启动] 登录/加载任务失败: {e}")
    
    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle('Kuzflow客制工作流')
        self.setGeometry(100, 100, 960, 640)

        # 设置窗口图标（使用打包兼容的资源路径）
        try:
            icon = QIcon(resource_path("public/logo.png"))
            if not icon.isNull():
                self.setWindowIcon(icon)
                print("[UI] 窗口图标设置成功")
            else:
                print("[UI] 窗口图标加载失败，使用默认图标")
        except Exception as e:
            print(f"[UI] 窗口图标设置异常: {e}")

        # 顶层垂直布局（包含：页头 + 主体分栏）
        layout = QVBoxLayout()

        # ========== 页头（Logo + 标题 + 系统状态 + 登出） ==========
        header_frame = QFrame()
        header_frame.setObjectName("header")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)

        # 左侧：Logo 与标题
        logo_and_title = QHBoxLayout()
        logo_and_title.setSpacing(8)
        logo_and_title.setContentsMargins(0, 0, 0, 0)
        logo_label = QLabel()
        logo_label.setFixedSize(32, 32)
        logo_label.setAlignment(Qt.AlignCenter)
        try:
            pix = QPixmap(resource_path("public/logo.png"))
            if not pix.isNull():
                logo_label.setPixmap(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass
        title_area = QVBoxLayout()
        title_area.setContentsMargins(0, 0, 0, 0)
        title_area.setSpacing(0)
        self.word_label = QLabel('科智流 KUZFLOW')
        subtitle_label = QLabel('智能流程自动化管理平台')
        subtitle_label.setObjectName("subTitle")
        title_area.addWidget(self.word_label)
        title_area.addWidget(subtitle_label)
        title_area.addStretch()
        logo_and_title.addWidget(logo_label)
        # 使用容器包裹标题区，便于对齐控制
        title_container = QWidget()
        title_container.setLayout(title_area)
        logo_and_title.addWidget(title_container)
        logo_and_title.setAlignment(logo_label, Qt.AlignVCenter)
        logo_and_title.setAlignment(title_container, Qt.AlignVCenter)

        # 右侧：系统状态 + 登出
        right_header = QHBoxLayout()
        right_header.setSpacing(8)
        right_header.setContentsMargins(0, 0, 0, 0)
        right_header.addStretch()
        self.status_badge = QLabel('系统状态: 待机')
        self.status_badge.setObjectName("statusBadge")
        # 限制尺寸，避免把页头高度与宽度撑大
        self.status_badge.setFixedHeight(24)
        self.status_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.logout_button = FluentButton('登出')
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.clicked.connect(self.logout_user)
        right_header.addWidget(self.status_badge)
        right_header.addWidget(self.logout_button)

        # 用容器包裹左侧布局，确保在 header 中垂直居中
        left_container = QWidget()
        left_container.setLayout(logo_and_title)
        header_layout.addWidget(left_container)
        header_layout.setAlignment(left_container, Qt.AlignVCenter)
        header_layout.addLayout(right_header)
        layout.addWidget(header_frame)

        # ========== 主体：左右分栏 ==========
        content_layout = QHBoxLayout()

        # ---------------- 左侧（执行设置 + 任务管理） ----------------
        left_col = QVBoxLayout()

        # 执行设置卡片
        exec_card = QFrame()
        exec_card.setObjectName("card")
        exec_v = QVBoxLayout(exec_card)
        exec_v.setSpacing(8)
        exec_title = QLabel('执行设置')
        exec_title.setObjectName("sectionTitle")
        exec_v.addWidget(exec_title)

        # 循环设置区域（原始控件保持不变）
        loop_group = QVBoxLayout()
        loop_title = QLabel('循环执行')
        loop_title.setObjectName("subSectionTitle")
        loop_group.addWidget(loop_title)

        # 顶部行：说明 + 开关（Switch风格）
        loop_row = QHBoxLayout()
        loop_desc = QLabel('启用后将持续执行选定的任务')
        # 为了保持与参考风格一致的浅色 OFF 轨道，这里统一使用 QCheckBox + QSS 实现开关外观
        # 使用自定义 ToggleSwitch，使外观与交互完全一致
        self.enable_loop_checkbox = ToggleSwitch()
        self.enable_loop_checkbox.toggled.connect(
            lambda checked: self.on_loop_enabled_changed(Qt.Checked if checked else Qt.Unchecked)
        )
        loop_row.addWidget(loop_desc)
        loop_row.addStretch()
        loop_row.addWidget(self.enable_loop_checkbox)
        loop_group.addLayout(loop_row)

        # 启用时显示的参数概览
        self.loop_info_label = QLabel('')
        self.loop_info_label.setObjectName('hint')
        self.loop_info_label.setVisible(False)
        loop_group.addWidget(self.loop_info_label)

        # 循环次数设置（主页面隐藏，改由弹窗配置）
        loop_count_row = QWidget()
        loop_count_layout = QHBoxLayout(loop_count_row)
        loop_count_layout.setContentsMargins(0, 0, 0, 0)
        loop_count_label = QLabel('每组运行次数:')
        self.loop_count_spinbox = QSpinBox()
        self.loop_count_spinbox.setMinimum(1)
        self.loop_count_spinbox.setMaximum(999)
        self.loop_count_spinbox.setValue(1)
        self.loop_count_spinbox.setEnabled(False)
        loop_count_layout.addWidget(loop_count_label)
        loop_count_layout.addWidget(self.loop_count_spinbox)
        loop_count_layout.addStretch()
        loop_group.addWidget(loop_count_row)
        loop_count_row.setVisible(False)

        # 循环间隔设置（主页面隐藏，改由弹窗配置）
        loop_interval_row = QWidget()
        loop_interval_layout = QHBoxLayout(loop_interval_row)
        loop_interval_layout.setContentsMargins(0, 0, 0, 0)
        loop_interval_label = QLabel('每组间隔(秒):')
        self.loop_interval_spinbox = QSpinBox()
        self.loop_interval_spinbox.setMinimum(0)
        self.loop_interval_spinbox.setMaximum(2147483647)
        self.loop_interval_spinbox.setValue(60)
        self.loop_interval_spinbox.setEnabled(False)
        loop_interval_layout.addWidget(loop_interval_label)
        loop_interval_layout.addWidget(self.loop_interval_spinbox)
        loop_interval_layout.addStretch()
        loop_group.addWidget(loop_interval_row)
        loop_interval_row.setVisible(False)

        exec_v.addLayout(loop_group)
        left_col.addWidget(exec_card)

        # 任务管理卡片
        task_card = QFrame()
        task_card.setObjectName("card")
        task_v = QVBoxLayout(task_card)
        task_v.setSpacing(8)
        task_v.setContentsMargins(10, 8, 10, 10)
        task_title = QLabel('任务管理')
        task_title.setObjectName("sectionTitle")
        task_v.addWidget(task_title)

        # 创建可滚动的执行按钮区域（沿用原逻辑）
        scroll_area = QScrollArea()
        scroll_area.setObjectName("taskScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        # 改为网格布局，模仿卡片网格
        grid_layout = QGridLayout(scroll_widget)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(12)

        # 动态按钮容器：初始化为空，稍后由 fetch_and_render_tasks 填充
        self.dynamic_buttons_layout = grid_layout
        self.task_scroll_widget = scroll_widget
        scroll_area.setWidget(scroll_widget)
        # 让可见区域展示 2 行卡片（2x2 可见），多余部分滚动
        vsp = grid_layout.verticalSpacing()
        if vsp < 0:
            vsp = 12
        task_card_min_h = 124
        scroll_area.setFixedHeight(task_card_min_h * 2 + vsp + 16)
        task_v.addWidget(scroll_area)

        # 操作按钮（保留原功能）
        actions_row = QHBoxLayout()
        self.stop_button = FluentPrimaryButton('停止循环')
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.clicked.connect(self.stop_process)
        self.stop_button.setEnabled(False)
        actions_row.addWidget(self.stop_button)
        task_v.addLayout(actions_row)

        left_col.addWidget(task_card)

        # ---------------- 右侧（系统日志） ----------------
        right_col = QVBoxLayout()
        logs_card = QFrame()
        logs_card.setObjectName("card")
        logs_v = QVBoxLayout(logs_card)
        logs_title = QLabel('系统日志')
        logs_title.setObjectName("sectionTitle")
        logs_v.addWidget(logs_title)

        # 状态显示区域（沿用原 QTextEdit 与逻辑）
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("状态信息将在这里显示...")
        # 日志顶部工具条（仅展示，不改变功能）
        toolbar = QHBoxLayout()
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText('搜索日志...')
        self.logs_count_label = QLabel('0 条记录')
        export_btn = FluentButton('导出')
        export_btn.setEnabled(False)  # 仅展示，不改动功能
        toolbar.addWidget(self.log_search)
        toolbar.addWidget(self.logs_count_label)
        toolbar.addWidget(export_btn)
        logs_v.addLayout(toolbar)

        logs_v.addWidget(self.status_text)
        right_col.addWidget(logs_card)

        # 组装左右列
        content_layout.addLayout(left_col)
        content_layout.addLayout(right_col)
        content_layout.setStretch(0, 2)
        content_layout.setStretch(1, 1)
        layout.addLayout(content_layout)

        # 4. 输入框（保留原有功能，暂时隐藏）
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText('请输入内容...')
        self.input_box.setVisible(False)
        layout.addWidget(self.input_box)

        # 统一放大并自适应字体（以应用默认字号为基准进行微调）
        # 获取当前应用默认字体的字号作为基准，保证跨DPI一致显示
        base_point_size = max(1, self.font().pointSize())
        base_family = self.font().family()

        # 标题稍大且加粗（再小一档）
        title_font = QFont(base_family, base_point_size + 3, QFont.Bold)
        self.word_label.setFont(title_font)

        # 分组标题加粗（不额外放大）
        group_title_font = QFont(base_family, base_point_size, QFont.Bold)
        loop_title.setFont(group_title_font)

        # 普通标签/复选框更小一档，输入框使用基础字号-1
        label_font = QFont(base_family, max(1, base_point_size - 2))
        strong_label_font = QFont(base_family, max(1, base_point_size - 1))
        self.enable_loop_checkbox.setFont(label_font)
        # 两个小标签
        loop_count_label.setFont(label_font)
        loop_interval_label.setFont(label_font)
        # 输入框
        self.input_box.setFont(strong_label_font)

        # 按钮使用基础字号（继续减小）
        button_font = QFont(base_family, base_point_size)
        # 动态按钮的字体会在 fetch_and_render_tasks 中设置
        self.button_font = button_font  # 保存字体供动态按钮使用
        self.stop_button.setFont(button_font)
        self.logout_button.setFont(button_font)

        # 状态文本使用更小的等宽字体（再小一档），便于显示更多日志内容
        status_font = QFont("monospace", max(1, base_point_size - 2))
        self.status_text.setFont(status_font)

        # 打印当前各区域字号设置，便于调试
        print(f"[UI] 字号设置: base={base_point_size}pt, title={title_font.pointSize()}pt, "
              f"groupTitle={group_title_font.pointSize()}pt, button={button_font.pointSize()}pt, "
              f"status={status_font.pointSize()}pt")

        # 设置布局
        self.setLayout(layout)

        # 初始化状态徽标
        self._set_global_status_text("待机")
        self.logs_count = 0

        # 应用深色主题与卡片QSS
        self._apply_dark_qss()

    def _set_global_status_text(self, text: str):
        """更新右上角系统状态文本（纯UI，不改变业务逻辑）"""
        try:
            if hasattr(self, 'status_badge') and isinstance(self.status_badge, QLabel):
                self.status_badge.setText(f"系统状态: {text}")
        except Exception:
            pass

    def _apply_dark_qss(self):
        """应用深色主题 + 卡片样式（仅QSS，不影响功能）
        - 颜色参考: React 设计 #0B0F10 背景、#01CBCB 主色、#DFEEEE 文本
        - 使用 objectName 精准作用在本窗口组件
        """
        app = QApplication.instance()
        if not app:
            return
        qss = """
        /* 主窗口背景 - 只对根窗口设置背景色 */
        SimpleApp { background-color: #0B0F10; }
        
        /* 所有文本标签使用透明背景 */
        QLabel { background: transparent; color: #DFEEEE; }
        
        /* 其他组件默认透明背景 */
        QWidget { background: transparent; color: #DFEEEE; }
        
        QFrame#card { 
            background-color: rgba(223,238,238,0.08);
            border: 1px solid rgba(223,238,238,0.18);
            border-radius: 12px; 
            padding: 10px;
            /* 增强玻璃态效果 */
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 
                        0 2px 8px rgba(0, 0, 0, 0.08), 
                        inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }
        QFrame#header { 
            background: transparent; 
            padding: 4px; 
        }
        QLabel#sectionTitle { 
            background: transparent; 
            font-weight: 600; 
            font-size: 13pt; 
            color: #DFEEEE; 
        }
        QLabel#subSectionTitle { 
            background: transparent; 
            font-weight: 500; 
            color: #DFEEEE; 
        }
        QLabel#statusBadge { 
            background-color: transparent;
            border: 1px solid #01CBCB; 
            color: #01CBCB; 
            padding: 4px 8px; 
            border-radius: 10px;
            margin-right: 4px;
            min-width: 120px;
        }
        QPushButton { 
            background-color: rgba(223,238,238,0.08); 
            color: #DFEEEE; 
            border: 1px solid rgba(223,238,238,0.18);
            border-radius: 10px; 
            padding: 6px 10px;
        }
        QLabel#taskTitle { 
            background: transparent; 
            font-weight: 600; 
            color: #DFEEEE; 
        }
        QLabel#taskDesc { 
            background: transparent; 
            color: #b7c9c9; 
        }
        
        /* 其他标签样式 - 确保所有文本都有透明背景 */
        QLabel#hint { 
            background: transparent; 
            color: #DFEEEE; 
        }
        QLabel#subTitle { 
            background: transparent; 
            color: #b7c9c9; 
        }
        
        QPushButton:hover { border-color: rgba(1,203,203,0.3); }
        QPushButton#dangerButton {
            background-color: rgba(239,68,68,0.08);
            border: 1px solid rgba(239,68,68,0.3);
            color: #EF4444;
        }
        QPushButton#logoutButton {
            background-color: rgba(255,198,98,0.08);
            border: 1px solid rgba(255,198,98,0.3);
            color: #FFC662;
        }
        /* 登录对话框的按钮强调色 */
        QPushButton#loginPrimary {
            background-color: #01CBCB;
            color: #071A1A;
        }
        QLineEdit, QSpinBox { 
            background-color: rgba(223,238,238,0.08); 
            border: 1px solid rgba(223,238,238,0.18); 
            border-radius: 8px; padding: 4px 6px; color: #DFEEEE; }
        QTextEdit { 
            background-color: rgba(7,26,26,0.3); 
            border: 1px solid rgba(223,238,238,0.12); 
            border-radius: 8px; color: #DFEEEE; }
        QCheckBox { spacing: 6px; }
        QCheckBox::indicator { width: 14px; height: 14px; }
        QScrollArea#taskScroll { border: none; }

        /* Scrollbar styling - thin, rounded, teal handle */
        QScrollBar:vertical { 
            background: transparent; 
            width: 8px; 
            margin: 2px; 
            border: none; 
        }
        QScrollBar:horizontal { 
            background: transparent; 
            height: 8px; 
            margin: 2px; 
            border: none; 
        }
        QScrollBar::handle:vertical { 
            background: rgba(1,203,203,0.45); 
            min-height: 24px; 
            border-radius: 4px; 
        }
        QScrollBar::handle:vertical:hover { background: rgba(1,203,203,0.65); }
        QScrollBar::handle:horizontal { 
            background: rgba(1,203,203,0.45); 
            min-width: 24px; 
            border-radius: 4px; 
        }
        QScrollBar::handle:horizontal:hover { background: rgba(1,203,203,0.65); }
        QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; background: none; border: none; }
        QScrollBar::add-page, QScrollBar::sub-page { background: rgba(223,238,238,0.06); border-radius: 4px; }

        /* 任务卡片样式 - 增强对比度 */
        QFrame#taskCard { 
            background-color: rgba(1, 203, 203, 0.08);
            border: 1px solid rgba(1, 203, 203, 0.15);
            border-radius: 12px; 
            padding: 12px;
            /* 玻璃态效果 */
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1), 
                        0 1px 4px rgba(0, 0, 0, 0.06), 
                        inset 0 1px 0 rgba(1, 203, 203, 0.1);
        }
        QFrame#taskCard:hover {
            background-color: rgba(1, 203, 203, 0.12);
            border-color: rgba(1, 203, 203, 0.25);
            transform: translateY(-2px);
        }
        
        /*（自绘 ToggleSwitch 已替代 QCheckBox 样式，这里仅保留供其它勾选框使用）*/
        """
        app.setStyleSheet(qss)

    def do_login(self, username: str, password: str) -> bool:
        """执行登录：成功则设置 APIClient 默认用户
        - 返回 True/False 表示是否登录成功
        """
        self.log_status(f"[登录] 正在登录用户 {username} ...")
        client = APIClient(base_url="https://www.kuzflow.com", log_callback=self.log_status)
        ok, data = client.call_api("/api/login", {"user": username, "password": password}, method="POST")
        if not ok:
            self.log_status("❌ 登录失败，请检查账号/密码或后端配置")
            return False
        APIClient.set_default_user(username)
        self.log_status(f"✅ 登录成功，设置默认用户为 {username}")
        return True

    def fetch_and_render_tasks(self):
        """拉取任务并动态渲染按钮"""
        client = APIClient(base_url="https://www.kuzflow.com", log_callback=self.log_status)
        ok, data = client.call_api("/api/tasks", method="GET")
        tasks = data.get("tasks", []) if ok and isinstance(data, dict) else []
        self.log_status(f"📋 获取到 {len(tasks)} 个流程")

        # 清空旧按钮
        while self.dynamic_buttons_layout.count():
            item = self.dynamic_buttons_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # 生成新按钮
        row, col = 0, 0
        max_cols = 2  # 两列网格
        for name in tasks:
            # 卡片容器
            card = QFrame()
            card.setObjectName("taskCard")
            card_v = QVBoxLayout(card)
            card_v.setSpacing(6)
            card_v.setContentsMargins(10, 10, 10, 10)
            title = QLabel(name)
            title.setObjectName("taskTitle")
            desc = QLabel("来自后端的动态任务")
            desc.setObjectName("taskDesc")
            btn = FluentPrimaryButton("启动")
            btn.clicked.connect(lambda _, n=name: self._run_process(n))
            if hasattr(self, 'button_font'):
                btn.setFont(self.button_font)
            card_v.addWidget(title)
            card_v.addWidget(desc)
            card_v.addWidget(btn)
            self.dynamic_buttons_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        self.log_status("✅ 动态按钮生成完成")

    def show_login_dialog_and_load(self):
        """显示登录对话框（参考 React 登录页：Logo + 标题 + 卡片表单）"""
        dlg = QDialog(self)
        dlg.setWindowTitle("登录")
        dlg.setModal(True)
        dlg.setMinimumWidth(460)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # 顶部 Logo 与标题
        logo_wrap = QVBoxLayout()
        logo_wrap.setAlignment(Qt.AlignHCenter)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        try:
            pixmap = QPixmap(resource_path("public/logo.png"))
            if not pixmap.isNull():
                logo.setPixmap(pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass
        title = QLabel("科智流 KUZFLOW")
        subtitle = QLabel("智能流程自动化平台")
        title.setAlignment(Qt.AlignCenter)
        subtitle.setAlignment(Qt.AlignCenter)
        logo_wrap.addWidget(logo)
        logo_wrap.addWidget(title)
        logo_wrap.addWidget(subtitle)
        root.addLayout(logo_wrap)

        # 卡片
        card = QFrame()
        card.setObjectName("card")
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(20, 20, 20, 20)
        card_v.setSpacing(12)

        header = QLabel("登录您的账户")
        header.setAlignment(Qt.AlignCenter)
        card_v.addWidget(header)

        user_edit = FluentLineEdit()
        user_edit.setPlaceholderText("账号")
        pwd_edit = FluentLineEdit()
        pwd_edit.setPlaceholderText("密码")
        pwd_edit.setEchoMode(QLineEdit.Password)

        card_v.addWidget(user_edit)
        card_v.addWidget(pwd_edit)

        remember_row = QHBoxLayout()
        remember_row.addWidget(QCheckBox("记住我"))
        remember_row.addStretch()
        card_v.addLayout(remember_row)

        actions = QHBoxLayout()
        btn_login = FluentPrimaryButton("登录")
        btn_cancel = FluentButton("取消")
        btn_login.setObjectName("loginPrimary")
        btn_cancel.setObjectName("loginCancel")
        actions.addWidget(btn_login, 1)
        actions.addWidget(btn_cancel)
        card_v.addLayout(actions)

        root.addWidget(card)

        # 事件绑定
        def on_login():
            username = user_edit.text().strip()
            password = pwd_edit.text().strip()
            if not username or not password:
                self.log_status("⚠️ 请输入账号与密码")
                return
            if self.do_login(username, password):
                dlg.accept()
            else:
                self.log_status("❌ 登录失败，请重试")

        btn_login.clicked.connect(on_login)
        btn_cancel.clicked.connect(dlg.reject)

        # 显示对话框并等待
        if dlg.exec_() == QDialog.Accepted:
            self.login_ok = True
            # 启动阶段不立即 show，由 main 统一处理；登出场景需重新显示
            if not self.isVisible():
                pass
            else:
                self.show()
            self.fetch_and_render_tasks()
        else:
            # 取消/关闭：启动阶段由 main 直接退出；登出场景直接退出应用
            self.login_ok = False
            if self.isVisible():
                self.log_status("🚪 已取消登录，退出应用")
                QApplication.instance().quit()

    def logout_user(self):
        """登出：停止流程、清空按钮、清除默认用户并重新登录"""
        # 停止当前流程
        if self.process_thread and self.process_thread.isRunning():
            self.stop_process()
        # 清空动态按钮
        while self.dynamic_buttons_layout.count():
            item = self.dynamic_buttons_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        # 清除默认用户
        APIClient.set_default_user(None)
        self.log_status("👋 已登出")
        # 隐藏主界面，仅显示登录窗口
        self.hide()
        # 重新登录
        self.show_login_dialog_and_load()
    
    def on_loop_enabled_changed(self, state):
        """循环启用：打开时弹窗确认，确定才真正启用；取消/关闭则还原为关闭"""
        enabled = state == Qt.Checked
        if enabled:
            ok, runs, interval = self._prompt_loop_config(
                default_runs=self.loop_count_spinbox.value(),
                default_interval=self.loop_interval_spinbox.value(),
            )
            if ok:
                try:
                    self.loop_count_spinbox.setValue(int(runs))
                    self.loop_interval_spinbox.setValue(int(interval))
                except Exception:
                    pass
                self.loop_count_spinbox.setEnabled(True)
                self.loop_interval_spinbox.setEnabled(True)
                self.loop_info_label.setVisible(True)
                self.loop_info_label.setText(
                    f"每组运行{self.loop_count_spinbox.value()}次，间隔{self.loop_interval_spinbox.value()}秒"
                )
            else:
                # 取消或关闭：还原开关为关闭
                self.enable_loop_checkbox.blockSignals(True)
                self.enable_loop_checkbox.setChecked(False)
                self.enable_loop_checkbox.blockSignals(False)
                self.loop_count_spinbox.setEnabled(False)
                self.loop_interval_spinbox.setEnabled(False)
                self.loop_info_label.setVisible(False)
        else:
            # 关闭：禁用参数、隐藏概要
            self.loop_count_spinbox.setEnabled(False)
            self.loop_interval_spinbox.setEnabled(False)
            self.loop_info_label.setVisible(False)

    def _prompt_loop_config(self, default_runs: int = 1, default_interval: int = 60):
        """弹出循环执行设置对话框，返回 (ok, runs, interval)"""
        dlg = QDialog(self)
        dlg.setWindowTitle("循环执行设置")
        v = QVBoxLayout(dlg)

        title = QLabel("配置循环执行的参数设置")
        v.addWidget(title)

        # 每组运行次数
        row1 = QVBoxLayout()
        label_runs = QLabel("每组运行次数")
        input_runs = QSpinBox()
        input_runs.setMinimum(1)
        input_runs.setMaximum(999)
        input_runs.setValue(int(default_runs) if default_runs else 1)
        row1.addWidget(label_runs)
        row1.addWidget(input_runs)
        v.addLayout(row1)

        # 每组间隔秒数
        row2 = QVBoxLayout()
        label_itv = QLabel("每组间隔秒数")
        input_itv = QSpinBox()
        input_itv.setMinimum(0)
        input_itv.setMaximum(2147483647)
        input_itv.setValue(int(default_interval) if default_interval is not None else 60)
        row2.addWidget(label_itv)
        row2.addWidget(input_itv)
        v.addLayout(row2)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_cancel = FluentButton("取消")
        btn_ok = FluentPrimaryButton("确定")
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        v.addLayout(btn_row)

        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)

        ok = dlg.exec_() == QDialog.Accepted
        return ok, input_runs.value(), input_itv.value()
    
    def log_status(self, message):
        """添加状态信息到显示区域"""
        self.status_text.append(message)
        self.status_text.ensureCursorVisible()
        QApplication.processEvents()  # 立即更新UI
        # 更新日志计数徽标（仅展示）
        try:
            self.logs_count += 1
            if hasattr(self, 'logs_count_label'):
                self.logs_count_label.setText(f"{self.logs_count} 条记录")
        except Exception:
            pass
    
    def _run_process(self, task_name: str):
        """执行流程（支持循环）"""
        if self.process_thread and self.process_thread.isRunning():
            self.log_status("⚠️ 已有流程正在执行中，请先停止")
            return
            
        # 获取循环设置
        enable_infinite_loop = self.enable_loop_checkbox.isChecked()
        if enable_infinite_loop:
            loop_count = self.loop_count_spinbox.value()
            loop_interval = self.loop_interval_spinbox.value()
            self.log_status(f"🔄 启用循环模式: 每组运行 {loop_count} 次，组间间隔 {loop_interval} 秒")
        else:
            loop_count = 1
            loop_interval = 0
            self.log_status("▶️ 单次执行模式")
        
        # 禁用按钮，启用停止按钮
        self.set_buttons_enabled(False)
        self.stop_button.setEnabled(True)
        
        # 创建并启动线程
        self.process_thread = ProcessThread(
            task_name=task_name,
            server_url="https://www.kuzflow.com",
            loop_count=loop_count,
            loop_interval=loop_interval,
            enable_infinite_loop=enable_infinite_loop  # 添加这个参数
        )
        self.process_thread.log_signal.connect(self.log_status)
        self.process_thread.finished_signal.connect(self.on_process_finished)
        self.process_thread.start()
        # 更新页头状态
        self._set_global_status_text("运行中")
    
    def stop_process(self):
        """停止正在执行的流程"""
        if self.process_thread and self.process_thread.isRunning():
            self.log_status("🛑 正在停止流程...")
            self.process_thread.stop()
            self.process_thread.wait()  # 等待线程结束
            self.on_process_finished(False)
    
    def on_process_finished(self, success):
        """流程执行完成的处理"""
        # 恢复按钮状态
        self.set_buttons_enabled(True)
        self.stop_button.setEnabled(False)
        
        if success:
            self.log_status("🎉 流程执行完成!")
        else:
            self.log_status("❌ 流程执行结束")
        # 更新页头状态
        self._set_global_status_text("待机")
    
    def set_buttons_enabled(self, enabled):
        """设置执行按钮的启用状态"""
        # 遍历滚动容器内的所有按钮并设置启用状态（兼容卡片包裹）
        try:
            if hasattr(self, 'task_scroll_widget') and self.task_scroll_widget:
                for btn in self.task_scroll_widget.findChildren(QPushButton):
                    # 跳过“停止循环”“登出”等全局按钮
                    if btn is self.stop_button or btn is self.logout_button:
                        continue
                    btn.setEnabled(enabled)
        except Exception:
            pass

    def start_process_douyin(self):
        self._run_process("截图识别")

    def start_process_drag(self):
        self._run_process("拖拽识别流程")
    def start_analyze_video(self):
        self._run_process("视频维度信息分析")
        
    def analyse_wirte_doc(self):
        self._run_process("视频数据分析流程")

    def start_analyze_account(self):
        """账号维度分析按钮对应的方法"""
        self._run_process("账号维度分析")

    def start_analyze_account_video(self):
        """抖音账号视频维度分析按钮对应的方法"""
        self._run_process("抖音账号视频维度分析")

    def daniel_test(self):
        """daniel测试按钮对应的方法"""
        self._run_process("daniel测试")


def main():
    # 1) 启用高DPI缩放与高清像素，需在 QApplication 创建前设置
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 2) 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（用于任务栏、Alt+Tab等）
    try:
        app_icon = QIcon(resource_path("public/logo.png"))
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
            print("[UI] 应用程序图标设置成功")
        else:
            print("[UI] 应用程序图标加载失败")
    except Exception as e:
        print(f"[UI] 应用程序图标设置异常: {e}")

    # 3) 根据屏幕DPI设置全局默认字体大小（点数），适度放大但较小于之前
    screen = app.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96.0
    scale = max(1.0, dpi / 96.0)
    base_point = int(round(12 * scale))
    default_font = QFont()
    default_font.setPointSize(base_point)
    app.setFont(default_font)

    # 打印阶段信息，便于排查
    print(f"[UI] 高DPI缩放已启用, DPI={dpi:.1f}, 基准字号={base_point}pt")

    window = SimpleApp()
    # 若用户在登录对话框中取消/关闭，则直接退出，不显示主窗口
    if getattr(window, 'login_ok', False):
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
