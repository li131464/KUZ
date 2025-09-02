# -*- coding: utf-8 -*-
"""
功能：
1) 启动多个 Edge 实例，每个使用独立 user-data-dir（实现独立 cookies）
2) 注册全局热键 = 在这些 Edge 窗口间循环切换

依赖：
    pip install keyboard pywin32 psutil
"""

import os
import sys
import time
import subprocess
from pathlib import Path

import psutil
import keyboard
import win32con
import win32gui
import win32process
import win32api


# ===================== 配置区域 =====================

# Edge 可执行文件路径（自动尝试常见位置，也可手动写死）
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# 启动的“独立会话”配置：每个 dict 对应一个 Edge 实例
PROFILES = [
    {"name": "p1", "url": "https://creator.douyin.com/creator-micro/home", "profile_directory": "Default"},
    {"name": "p2", "url": "https://creator.douyin.com/creator-micro/home", "profile_directory": "Default"},
    {"name": "p3", "url": "https://creator.douyin.com/creator-micro/home", "profile_directory": "Default"}
    # 如需更多会话，继续添加：{"name": "p3", "url": "...", "profile_directory": "Default"},
]

# 存放不同 user-data-dir 的根目录
USER_DATA_ROOT = str(Path.cwd() / "EdgeProfiles")

# 全局热键（在任意程序前台都生效）：=
GLOBAL_HOTKEY = "="

# ===================================================


def find_edge_path() -> str:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    # 从 PATH 搜索
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(p.strip('"'), "msedge.exe")
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError("未找到 msedge.exe，请检查 EDGE_CANDIDATES 或将 Edge 加入 PATH。")


def ensure_dir(p: str) -> str:
    Path(p).mkdir(parents=True, exist_ok=True)
    return p


def launch_edge_instances(edge_path: str):
    """启动多个 Edge，返回 Popen 列表"""
    procs = []
    for cfg in PROFILES:
        user_dir = ensure_dir(os.path.join(USER_DATA_ROOT, cfg["name"]))
        args = [
            edge_path,
            f'--user-data-dir="{user_dir}"',
            f'--profile-directory="{cfg.get("profile_directory", "Default")}"',
            cfg.get("url", "https://www.example.com"),
        ]
        # 使用 shell=False，避免命令行解析问题
        print("启动：", " ".join(args))
        procs.append(subprocess.Popen(" ".join(args), shell=False))
        time.sleep(0.4)  # 稍等一下让窗口起来
    return procs


def is_edge_window(hwnd: int) -> bool:
    """判断窗口是否为 Edge 顶层可见窗口"""
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False
    # 过滤掉没有标题的无效窗口
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False
    # 通过进程名判断
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        pname = psutil.Process(pid).name().lower()
        return pname == "msedge.exe"
    except Exception:
        return False


def enum_edge_windows() -> list[int]:
    """枚举当前所有 Edge 顶层窗口句柄"""
    result = []
    def callback(h, _):
        if is_edge_window(h):
            result.append(h)
    win32gui.EnumWindows(callback, None)
    # 去重并稳定排序（按句柄升序）
    result = sorted(set(result))
    return result


def bring_to_front(hwnd: int):
    """激活窗口到前台，保持原有窗口状态（最大化/正常/最小化）"""
    try:
        # 获取当前窗口状态
        placement = win32gui.GetWindowPlacement(hwnd)
        current_state = placement[1]  # showCmd 字段
        
        # 根据当前状态决定显示方式
        if current_state == win32con.SW_SHOWMINIMIZED:
            # 如果是最小化状态，需要先还原再判断原始状态
            # placement[2] 是还原后的状态（正常或最大化）
            restore_state = placement[2]
            if restore_state == win32con.SW_SHOWMAXIMIZED:
                # 原本是最大化，直接最大化显示
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
            else:
                # 原本是正常窗口，还原显示
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        elif current_state == win32con.SW_SHOWMAXIMIZED:
            # 如果已经是最大化，保持最大化
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        else:
            # 正常状态窗口，直接激活不改变大小
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        
        # 激活窗口到前台
        win32gui.SetForegroundWindow(hwnd)
        
    except Exception:
        # 某些情况下需要附加线程输入（提升前台权限），这里做简单兜底
        try:
            # 模拟一次 Alt 键，帮助切前台
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass


def switch_to_next_edge_window():
    edgers = enum_edge_windows()
    if not edgers:
        return

    cur = win32gui.GetForegroundWindow()
    # 如果当前不是 Edge，则激活第一扇
    if cur not in edgers:
        bring_to_front(edgers[0])
        return

    # 在列表里找到当前的下一个
    try:
        idx = edgers.index(cur)
        nxt = edgers[(idx + 1) % len(edgers)]
    except ValueError:
        nxt = edgers[0]

    bring_to_front(nxt)


def main():
    edge_path = find_edge_path()
    ensure_dir(USER_DATA_ROOT)

    # 1) 启动多个独立实例
    procs = launch_edge_instances(edge_path)

    # 2) 注册全局热键切换（监听所有键盘事件，包括代码模拟的）
    print(f"已注册全局热键：{GLOBAL_HOTKEY}（在多个 Edge 窗口间循环切换）")
    
    # 使用 on_press 监听所有按键事件（包括代码模拟的）
    def on_key_event(event):
        if event.event_type == keyboard.KEY_DOWN:  # 只处理按下事件
            # 检查是否为指定的热键
            if event.name == GLOBAL_HOTKEY:
                switch_to_next_edge_window()
    
    keyboard.on_press(on_key_event)

    try:
        keyboard.wait()  # 阻塞，直到 Ctrl+C 或进程被结束
    except KeyboardInterrupt:
        pass
    finally:
        # 可选：结束我们启动的 Edge 进程（通常你可能希望保留会话，不自动关）
        # for p in procs:
        #     with contextlib.suppress(Exception):
        #         p.terminate()
        print("退出。")


if __name__ == "__main__":
    main()