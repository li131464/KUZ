# manipulate 模块 - 自动化操作执行模块
from .executor import execute_process, execute_step
from .api_client import APIClient
from .recognition import get_screenshot_coordinates, recognize_screenshot, take_screenshot
from .input_operations import click_position, input_text, execute_click, execute_input
from .file_operations import save_result_to_file, append_result_to_file, save_json_result, execute_save_result
from .wait_operations import execute_wait, wait_for_page_load, wait_for_element_load
from .llm_operations import execute_llm_process, process_content_with_llm, validate_llm_result
from .feishu_operations import execute_feishu_write
from .drag_operations import execute_drag
from .scroll_operations import execute_scroll
from .keyboard_operations import execute_keyboard
from .ocr_click_operations import execute_ocr_click, ocr_click_with_text

__all__ = [
    'execute_process',
    'execute_step', 
    'APIClient',
    'get_screenshot_coordinates',
    'recognize_screenshot',
    'take_screenshot',
    'click_position',
    'input_text',
    'execute_click',
    'execute_input',
    'save_result_to_file',
    'append_result_to_file',
    'save_json_result',
    'execute_save_result',
    'execute_wait',
    'wait_for_page_load',
    'wait_for_element_load',
    'execute_llm_process',
    'process_content_with_llm',
    'validate_llm_result',
    'execute_feishu_write',
    'execute_drag',
    'execute_ocr_click',
    'ocr_click_with_text'
]