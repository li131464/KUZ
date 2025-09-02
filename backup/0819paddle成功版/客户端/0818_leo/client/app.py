import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit
from PyQt5.QtCore import Qt

# 导入manipulate模块
from manipulate import execute_process

class SimpleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle('自动化流程测试')
        self.setGeometry(100, 100, 500, 400)
        
        # 创建垂直布局
        layout = QVBoxLayout()
        
        # 1. 一个单词标签
        self.word_label = QLabel('流程控制')
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.word_label)
        
        # 2. 两个按钮：分别执行两种流程
        self.start_douyin_button = QPushButton('执行：截图识别')
        self.start_douyin_button.clicked.connect(self.start_process_douyin)
        self.start_douyin_button.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.start_douyin_button)

        self.start_drag_button = QPushButton('执行：拖拽识别流程')
        self.start_drag_button.clicked.connect(self.start_process_drag)
        self.start_drag_button.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.start_drag_button)

        self.start_copy_button = QPushButton('执行：抖音信息复制流程')
        self.start_copy_button.clicked.connect(self.start_process_copy)
        self.start_copy_button.setStyleSheet("font-size: 14px; padding: 8px; background-color: #4CAF50; color: white;")
        layout.addWidget(self.start_copy_button)

        self.start_ocr_click_button = QPushButton('执行：OCR点击测试流程')
        self.start_ocr_click_button.clicked.connect(self.start_process_ocr_click)
        self.start_ocr_click_button.setStyleSheet("font-size: 14px; padding: 8px; background-color: #FF9800; color: white;")
        layout.addWidget(self.start_ocr_click_button)
        
        # 3. 一个输入框
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText('请输入内容...')
        self.input_box.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.input_box)
        
        # 4. 状态显示区域
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("background-color: #f0f0f0; font-family: monospace;")
        self.status_text.setPlaceholderText("状态信息将在这里显示...")
        layout.addWidget(self.status_text)
        
        # 设置布局
        self.setLayout(layout)
    
    def log_status(self, message):
        """添加状态信息到显示区域"""
        self.status_text.append(message)
        self.status_text.ensureCursorVisible()
        QApplication.processEvents()  # 立即更新UI
    
    def _run_process(self, task_name: str):
        self.log_status(f"🚀 开始执行流程：{task_name} ...")
        self.log_status("=" * 50)
        try:
            success = execute_process(
                task_name=task_name,
                log_callback=self.log_status,
                # server_url="https://121.4.65.242"
                # server_url="http://localhost:8000"
                server_url="https://www.kuzflow.com"
            )
            if success:
                self.log_status("=" * 50)
                self.log_status("🎉 自动化流程完成!")
            else:
                self.log_status("=" * 50)
                self.log_status("❌ 自动化流程失败!")
        except Exception as e:
            self.log_status(f"💥 流程异常: {str(e)}")

    def start_process_douyin(self):
        self._run_process("截图识别")

    def start_process_drag(self):
        self._run_process("拖拽识别流程")

    def start_process_copy(self):
        self._run_process("抖音信息复制流程")

    def start_process_ocr_click(self):
        self._run_process("OCR点击测试流程")


def main():
    app = QApplication(sys.argv)
    window = SimpleApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
