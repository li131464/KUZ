"""
独立更新器程序 - PyInstaller版本
专门负责下载并替换主程序exe文件
"""

import sys
import os
import requests
import subprocess
import time
import json
import shutil
import hashlib
import tempfile
from pathlib import Path
from urllib.parse import urljoin


def log_message(message):
    """输出日志消息"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [更新器] {message}"
    
    print(log_line)
    
    # 同时写入日志文件
    try:
        log_file = Path("updater.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass  # 日志写入失败不影响更新过程


def show_progress(current, total, message=""):
    """显示进度条"""
    if total > 0:
        percent = int((current / total) * 100)
        bar_length = 30
        filled_length = int(bar_length * current // total)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r进度: [{bar}] {percent}% {message}", end="", flush=True)
        
        if current == total:
            print()  # 完成后换行


def download_file(url, local_path, expected_size=0, expected_hash=""):
    """下载文件，支持进度显示和断点续传"""
    log_message(f"开始下载: {url}")
    log_message(f"保存到: {local_path}")
    
    try:
        # 检查是否支持断点续传
        resume_pos = 0
        headers = {}
        
        if os.path.exists(local_path):
            resume_pos = os.path.getsize(local_path)
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
                log_message(f"断点续传，从 {resume_pos} 字节开始")
        
        # 发起下载请求
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if response.status_code == 416:  # Range not satisfiable
            log_message("服务器不支持断点续传，重新下载")
            resume_pos = 0
            if os.path.exists(local_path):
                os.remove(local_path)
            response = requests.get(url, stream=True, timeout=30)
        
        response.raise_for_status()
        
        # 获取文件总大小
        total_size = resume_pos
        if response.status_code == 206:  # Partial content
            content_range = response.headers.get('Content-Range', '')
            if content_range:
                total_size = int(content_range.split('/')[-1])
        else:
            total_size = int(response.headers.get('Content-Length', 0))
        
        if expected_size > 0 and total_size > 0 and abs(total_size - expected_size) > 1024:
            log_message(f"警告: 文件大小不匹配 (期望: {expected_size}, 实际: {total_size})")
        
        # 下载文件
        downloaded = resume_pos
        mode = 'ab' if resume_pos > 0 else 'wb'
        
        with open(local_path, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 显示进度
                    if total_size > 0:
                        show_progress(downloaded, total_size, "下载中...")
        
        log_message(f"下载完成: {local_path} ({downloaded} 字节)")
        
        # 验证文件大小
        actual_size = os.path.getsize(local_path)
        if expected_size > 0 and abs(actual_size - expected_size) > 1024:
            raise Exception(f"文件大小验证失败: 期望 {expected_size} 字节, 实际 {actual_size} 字节")
        
        # 验证文件哈希
        if expected_hash:
            if not verify_file_hash(local_path, expected_hash):
                raise Exception("文件哈希验证失败")
        
        return True
        
    except requests.exceptions.RequestException as e:
        log_message(f"网络错误: {e}")
        return False
    except Exception as e:
        log_message(f"下载失败: {e}")
        return False


def verify_file_hash(file_path, expected_hash):
    """验证文件SHA256哈希值"""
    if not expected_hash:
        log_message("跳过文件哈希验证（未提供预期哈希值）")
        return True
    
    log_message("正在验证文件完整性...")
    
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        actual_hash = sha256_hash.hexdigest()
        
        if actual_hash.lower() == expected_hash.lower():
            log_message("✅ 文件完整性验证通过")
            return True
        else:
            log_message(f"❌ 文件哈希不匹配:")
            log_message(f"  期望: {expected_hash}")
            log_message(f"  实际: {actual_hash}")
            return False
            
    except Exception as e:
        log_message(f"文件哈希验证失败: {e}")
        return False


def backup_current_version(exe_path):
    """备份当前版本的exe文件"""
    try:
        if not os.path.exists(exe_path):
            log_message(f"主程序文件不存在: {exe_path}")
            return None
        
        # 创建备份目录
        backup_dir = Path("backup")
        backup_dir.mkdir(exist_ok=True)
        
        # 生成备份文件名
        timestamp = int(time.time())
        backup_filename = f"{Path(exe_path).stem}_backup_{timestamp}.exe"
        backup_path = backup_dir / backup_filename
        
        # 执行备份
        shutil.copy2(exe_path, backup_path)
        log_message(f"✅ 已备份当前版本到: {backup_path}")
        
        return str(backup_path)
        
    except Exception as e:
        log_message(f"❌ 备份失败: {e}")
        return None


def restore_from_backup(backup_path, target_path):
    """从备份恢复"""
    try:
        if not backup_path or not os.path.exists(backup_path):
            log_message("❌ 备份文件不存在，无法恢复")
            return False
        
        # 删除损坏的文件
        if os.path.exists(target_path):
            os.remove(target_path)
        
        # 恢复备份
        shutil.copy2(backup_path, target_path)
        log_message(f"✅ 已从备份恢复: {target_path}")
        
        return True
        
    except Exception as e:
        log_message(f"❌ 恢复备份失败: {e}")
        return False


def wait_for_process_exit(process_name, max_wait_time=10):
    """等待指定进程退出"""
    log_message(f"等待进程退出: {process_name}")
    
    import psutil
    
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        found_process = False
        
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    found_process = True
                    break
        except Exception:
            pass
        
        if not found_process:
            log_message(f"✅ 进程 {process_name} 已退出")
            return True
        
        time.sleep(0.5)
    
    log_message(f"⚠️ 等待进程退出超时: {process_name}")
    return False


def replace_executable(new_exe_path, target_exe_path):
    """替换可执行文件"""
    try:
        log_message(f"正在替换主程序...")
        log_message(f"  源文件: {new_exe_path}")
        log_message(f"  目标文件: {target_exe_path}")
        
        # 确保目标文件没有被锁定
        max_retries = 10
        for attempt in range(max_retries):
            try:
                # 删除旧文件
                if os.path.exists(target_exe_path):
                    os.remove(target_exe_path)
                    log_message(f"✅ 已删除旧文件: {target_exe_path}")
                
                # 移动新文件
                shutil.move(new_exe_path, target_exe_path)
                log_message(f"✅ 文件替换成功")
                
                return True
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    log_message(f"文件被占用，等待后重试... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    raise e
            except Exception as e:
                log_message(f"❌ 替换文件失败: {e}")
                return False
        
        return False
        
    except Exception as e:
        log_message(f"❌ 替换可执行文件失败: {e}")
        return False


def start_updated_application(exe_path):
    """启动更新后的应用程序"""
    try:
        log_message(f"正在启动更新后的应用程序: {exe_path}")
        
        if not os.path.exists(exe_path):
            raise Exception(f"更新后的程序文件不存在: {exe_path}")
        
        # 启动新程序
        subprocess.Popen([exe_path], cwd=str(Path(exe_path).parent))
        log_message("✅ 应用程序启动成功")
        
        return True
        
    except Exception as e:
        log_message(f"❌ 启动应用程序失败: {e}")
        return False


def cleanup_temp_files(temp_dir):
    """清理临时文件"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            log_message(f"✅ 清理临时文件: {temp_dir}")
    except Exception as e:
        log_message(f"清理临时文件失败: {e}")


def update_application():
    """主更新函数"""
    log_message("=" * 60)
    log_message("🚀 Kuzflow 应用更新器启动")
    log_message("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) < 3:
        log_message("❌ 参数不足！")
        log_message("用法: updater.exe <update_info.json> <target_exe_name>")
        input("按回车键退出...")
        return False
    
    update_info_file = sys.argv[1]
    target_exe_name = sys.argv[2]
    
    # 获取工作目录
    current_dir = Path.cwd()
    target_exe_path = current_dir / target_exe_name
    
    log_message(f"更新信息文件: {update_info_file}")
    log_message(f"目标程序: {target_exe_path}")
    log_message(f"工作目录: {current_dir}")
    
    backup_path = None
    temp_exe_path = None
    
    try:
        # 1. 读取更新信息
        log_message("📖 读取更新信息...")
        
        if not os.path.exists(update_info_file):
            raise Exception(f"更新信息文件不存在: {update_info_file}")
        
        with open(update_info_file, 'r', encoding='utf-8') as f:
            update_info = json.load(f)
        
        new_version = update_info['latest_version']
        download_url = update_info['download_url']
        expected_size = update_info.get('file_size', 0)
        expected_hash = update_info.get('file_hash', '')
        
        log_message(f"目标版本: v{new_version}")
        log_message(f"下载地址: {download_url}")
        log_message(f"文件大小: {expected_size} 字节")
        
        # 2. 等待主程序完全退出
        log_message("⏳ 等待主程序退出...")
        time.sleep(3)  # 给主程序足够时间退出
        
        # 尝试等待进程退出（需要psutil，如果没有就跳过）
        try:
            import psutil
            wait_for_process_exit(target_exe_name, 10)
        except ImportError:
            log_message("psutil未安装，跳过进程等待检查")
            time.sleep(2)  # 额外等待2秒
        
        # 3. 备份当前版本
        log_message("💾 备份当前版本...")
        backup_path = backup_current_version(target_exe_path)
        
        # 4. 准备临时目录
        temp_dir = current_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_exe_path = temp_dir / f"new_{target_exe_name}"
        
        # 5. 构建完整下载URL
        if not download_url.startswith('http'):
            # 从配置文件读取服务器地址
            config_file = current_dir / "config" / "update_config.json"
            base_url = "http://127.0.0.1:8000"
            
            try:
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        base_url = config.get("update_server", {}).get("base_url", base_url)
            except Exception as e:
                log_message(f"读取配置文件失败，使用默认URL: {e}")
            
            download_url = urljoin(base_url, download_url.lstrip('/'))
            log_message(f"完整下载URL: {download_url}")
        
        # 6. 下载新版本
        log_message("📥 下载新版本...")
        if not download_file(download_url, temp_exe_path, expected_size, expected_hash):
            raise Exception("下载新版本失败")
        
        # 7. 替换主程序文件
        log_message("🔄 替换主程序文件...")
        if not replace_executable(str(temp_exe_path), str(target_exe_path)):
            raise Exception("替换主程序文件失败")
        
        # 8. 验证替换结果
        if not os.path.exists(target_exe_path):
            raise Exception("替换后的程序文件不存在")
        
        # 9. 更新版本文件（必须在启动新程序前更新）
        try:
            version_file_path = current_dir / "version.txt"
            with open(version_file_path, 'w', encoding='utf-8') as f:
                f.write(new_version)
            log_message(f"✅ 版本文件已更新: {version_file_path} -> {new_version}")
        except Exception as e:
            log_message(f"⚠️ 更新版本文件失败: {e}")
        
        # 10. 启动新程序
        log_message("🚀 启动更新后的应用程序...")
        if not start_updated_application(str(target_exe_path)):
            log_message("⚠️ 自动启动失败，请手动启动应用程序")
        
        # 11. 清理临时文件
        log_message("🧹 清理临时文件...")
        cleanup_temp_files(str(temp_dir))
        
        # 清理更新信息文件
        try:
            if os.path.exists(update_info_file):
                os.remove(update_info_file)
        except Exception:
            pass
        
        log_message("=" * 60)
        log_message("🎉 更新完成！")
        log_message(f"应用程序已更新到版本 v{new_version}")
        log_message("=" * 60)
        
        return True
        
    except Exception as e:
        log_message("=" * 60)
        log_message(f"❌ 更新失败: {e}")
        log_message("=" * 60)
        
        # 尝试恢复备份
        if backup_path and os.path.exists(str(target_exe_path)):
            log_message("🔄 尝试恢复备份...")
            if restore_from_backup(backup_path, str(target_exe_path)):
                log_message("✅ 已恢复到更新前的版本")
                
                # 尝试启动原版本
                try:
                    start_updated_application(str(target_exe_path))
                except Exception:
                    log_message("⚠️ 请手动启动应用程序")
            else:
                log_message("❌ 恢复备份失败")
        
        # 清理可能的临时文件
        if temp_exe_path and os.path.exists(temp_exe_path):
            try:
                os.remove(temp_exe_path)
            except Exception:
                pass
        
        print(f"\n更新失败原因: {str(e)}")
        input("按回车键退出...")
        return False


def main():
    """主入口函数"""
    try:
        success = update_application()
        
        if success:
            log_message("更新器即将退出...")
            time.sleep(2)  # 给用户时间看到成功消息
        else:
            # 失败时等待用户确认
            input("按回车键退出...")
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        log_message("用户中断更新过程")
        return 1
    except Exception as e:
        log_message(f"更新器异常: {e}")
        input("按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())