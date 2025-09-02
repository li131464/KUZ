#!/usr/bin/env python3
import pyautogui
import time

# 禁用安全功能
pyautogui.FAILSAFE = False

def find_target_coordinates():
    """找到目标控件的准确坐标"""
    print("🎯 坐标查找工具")
    print("=" * 30)
    
    # 获取屏幕尺寸
    screen_size = pyautogui.size()
    print(f"屏幕尺寸: {screen_size}")
    
    while True:
        # 获取当前鼠标位置
        x, y = pyautogui.position()
        print(f"\r当前坐标: X={x:4d}, Y={y:4d}", end="")
        
        # 循环持续输出当前鼠标坐标，按 Ctrl+C 可中断
        # 这里不做额外判断，保证输出尽可能流畅
        time.sleep(0.1)

if __name__ == "__main__":
    # 程序启动后直接进入“实时坐标监控”模式，不再提供交互式选择
    print("1. 实时坐标监控")
    print("步骤：")
    print(" - 将鼠标移动到任意位置以查看其坐标")
    print(" - 按 Ctrl+C 结束程序")
    print("移动鼠标到目标位置，按 Ctrl+C 退出")
    try:
        find_target_coordinates()
    except KeyboardInterrupt:
        print("\n退出")
