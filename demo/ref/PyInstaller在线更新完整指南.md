# PyInstaller在线更新完整指南 - 超级小白版

## 🎯 问题背景

你有一个用PyQt5开发的应用程序，使用了conda环境和各种依赖包（如PaddleOCR等）。现在你想：

1. **用PyInstaller打包成exe文件**发布给用户
2. **实现在线更新功能**，让用户可以自动更新到新版本
3. **支持环境变化**，比如新版本添加了新的依赖包

但是遇到了一个关键问题：**PyInstaller打包后的exe文件在运行时无法自我替换！**

## 🔍 为什么普通的更新方案不行？

### ❌ 问题1：文件锁定

```
❌ 这样不行：
MyApp.exe (正在运行) → 尝试替换自己 → Windows说：文件被占用，无法替换
```

### ❌ 问题2：环境打包

```
❌ 这样不行：
当前demo的更新方案 → 替换Python源码文件 → 但PyInstaller已经把所有东西打包进exe了
```

## ✅ 解决方案：双程序更新模式

### 核心思路

```
🎯 关键思路：
不让程序自己更新自己，而是让另一个程序来更新它！
```

## 📁 新的项目结构

```
发布给用户的文件夹：
MyKuzflowApp/
├── KuzflowApp.exe          ← 主程序（你的应用）
├── updater.exe             ← 更新器程序（专门负责更新）
├── config/
│   └── update_config.json  ← 更新配置
├── data/                   ← 用户数据（更新时保留）
│   └── user_settings.json
└── temp/                   ← 临时文件夹
```

## 🔄 更新流程详解

### 第1步：检查更新

```
KuzflowApp.exe 启动
         ↓
    联网检查服务器
         ↓
   发现有新版本v1.1.0
         ↓
    弹出更新对话框
```

### 第2步：启动更新器

```
用户点击"立即更新"
         ↓
KuzflowApp.exe 告诉 updater.exe："帮我更新到v1.1.0"
         ↓
KuzflowApp.exe 自己退出（这样文件就不被锁定了）
         ↓
updater.exe 开始工作
```

### 第3步：执行更新

```
updater.exe 从服务器下载 new_KuzflowApp.exe
         ↓
备份旧的 KuzflowApp.exe（以防更新失败）
         ↓
删除旧的 KuzflowApp.exe
         ↓
将 new_KuzflowApp.exe 重命名为 KuzflowApp.exe
         ↓
启动新的 KuzflowApp.exe
         ↓
updater.exe 自己退出
```

## 📝 详细代码实现

### 1. 主程序中的更新检查代码

在你的主程序 `app.py` 中添加：

```python
import subprocess
import json
from pathlib import Path

class KuzflowMainApp:
    def check_for_updates(self):
        """检查更新的函数"""
        try:
            # 1. 调用服务器API检查更新
            api_client = APIClient("http://your-server.com")
            success, update_info = api_client.check_version("1.0.0")  # 当前版本
          
            if success and update_info.get("update_available"):
                # 2. 发现更新，询问用户
                reply = QMessageBox.question(
                    self,
                    "发现新版本",
                    f"发现新版本 {update_info['latest_version']}，是否立即更新？",
                    QMessageBox.Yes | QMessageBox.No
                )
              
                if reply == QMessageBox.Yes:
                    # 3. 用户确认更新，启动更新器
                    self.start_updater(update_info)
                  
        except Exception as e:
            QMessageBox.warning(self, "更新检查失败", f"无法检查更新：{e}")
  
    def start_updater(self, update_info):
        """启动更新器程序"""
        try:
            # 1. 把更新信息保存到文件，让更新器知道要下载什么
            update_file = Path("temp/update_info.json")
            update_file.parent.mkdir(exist_ok=True)
          
            with open(update_file, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, ensure_ascii=False, indent=2)
          
            # 2. 启动更新器程序
            subprocess.Popen([
                "updater.exe",          # 更新器程序
                str(update_file),       # 告诉它更新信息文件在哪
                "KuzflowApp.exe"        # 告诉它要更新哪个文件
            ])
          
            # 3. 主程序退出，释放文件锁
            self.close()
            QApplication.quit()
          
        except Exception as e:
            QMessageBox.critical(self, "启动更新器失败", f"无法启动更新程序：{e}")
```

### 2. 独立的更新器程序

创建一个新文件 `updater.py`：

```python
import sys
import os
import requests
import subprocess
import time
import json
import shutil
import hashlib
from pathlib import Path
import tempfile

def log_message(message):
    """输出日志（你可以改成写入日志文件）"""
    print(f"[更新器] {message}")
    # 也可以写入日志文件
    with open("updater.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [更新器] {message}\n")

def download_file(url, local_path, expected_size=0):
    """下载文件，支持进度显示"""
    log_message(f"开始下载：{url}")
  
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
      
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
      
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                  
                    # 显示进度
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        log_message(f"下载进度：{percent:.1f}%")
      
        log_message(f"下载完成：{local_path}")
        return True
      
    except Exception as e:
        log_message(f"下载失败：{e}")
        return False

def verify_file(file_path, expected_hash):
    """验证文件完整性"""
    if not expected_hash:
        return True  # 如果没有提供哈希，跳过验证
  
    log_message("验证文件完整性...")
  
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
  
    actual_hash = sha256_hash.hexdigest()
  
    if actual_hash == expected_hash:
        log_message("文件完整性验证通过")
        return True
    else:
        log_message(f"文件完整性验证失败！期望：{expected_hash}，实际：{actual_hash}")
        return False

def backup_old_version(app_exe_path):
    """备份旧版本"""
    try:
        if os.path.exists(app_exe_path):
            backup_path = f"{app_exe_path}.backup_{int(time.time())}"
            shutil.copy2(app_exe_path, backup_path)
            log_message(f"已备份旧版本到：{backup_path}")
            return backup_path
        return None
    except Exception as e:
        log_message(f"备份失败：{e}")
        return None

def restore_backup(backup_path, app_exe_path):
    """恢复备份"""
    try:
        if backup_path and os.path.exists(backup_path):
            shutil.move(backup_path, app_exe_path)
            log_message("已恢复到备份版本")
            return True
    except Exception as e:
        log_message(f"恢复备份失败：{e}")
    return False

def update_application():
    """主更新函数"""
    if len(sys.argv) < 3:
        log_message("参数不足！用法：updater.exe <update_info.json> <app_exe_name>")
        input("按回车键退出...")
        return False
  
    update_info_file = sys.argv[1]  # temp/update_info.json
    app_exe_name = sys.argv[2]      # KuzflowApp.exe
  
    try:
        # 1. 读取更新信息
        log_message("读取更新信息...")
        with open(update_info_file, 'r', encoding='utf-8') as f:
            update_info = json.load(f)
      
        new_version = update_info['latest_version']
        download_url = update_info['download_url']
        expected_hash = update_info.get('file_hash', '')
      
        log_message(f"准备更新到版本：{new_version}")
      
        # 2. 等待主程序完全退出
        log_message("等待主程序退出...")
        time.sleep(2)  # 等待2秒确保主程序完全退出
      
        # 3. 下载新版本到临时文件
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_exe_path = temp_dir / f"new_{app_exe_name}"
      
        # 构建完整的下载URL
        if not download_url.startswith("http"):
            # 如果是相对URL，添加服务器地址
            server_base = "http://127.0.0.1:8000"  # 从配置文件读取
            download_url = f"{server_base}{download_url}"
      
        if not download_file(download_url, temp_exe_path):
            raise Exception("下载新版本失败")
      
        # 4. 验证文件
        if not verify_file(temp_exe_path, expected_hash):
            raise Exception("文件完整性验证失败")
      
        # 5. 备份旧版本
        backup_path = backup_old_version(app_exe_name)
      
        # 6. 替换主程序
        log_message("正在替换主程序...")
      
        # 删除旧文件
        if os.path.exists(app_exe_name):
            os.remove(app_exe_name)
      
        # 移动新文件
        shutil.move(str(temp_exe_path), app_exe_name)
      
        log_message("程序更新完成！")
      
        # 7. 启动新版本
        log_message("启动新版本...")
        subprocess.Popen([app_exe_name])
      
        # 8. 清理临时文件
        try:
            if os.path.exists(update_info_file):
                os.remove(update_info_file)
        except:
            pass
      
        log_message("更新成功完成！")
        return True
      
    except Exception as e:
        log_message(f"更新失败：{e}")
      
        # 尝试恢复备份
        if 'backup_path' in locals():
            log_message("尝试恢复备份...")
            restore_backup(backup_path, app_exe_name)
      
        input("更新失败！按回车键退出...")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Kuzflow 应用更新器")
    print("=" * 50)
  
    success = update_application()
  
    if not success:
        # 如果更新失败，等待用户按键
        input("按回车键退出...")
```

## 🔧 PyInstaller构建脚本

创建 `build.py` 文件来自动化构建过程：

```python
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理：{dir_name}")

def build_main_app():
    """构建主应用程序"""
    print("正在构建主应用程序...")
  
    PyInstaller.__main__.run([
        'app.py',                           # 你的主程序
        '--name=KuzflowApp',               # 生成的exe名称
        '--windowed',                      # 无控制台窗口
        '--onefile',                       # 打包成单个exe（也可以用--onedir）
        '--add-data=config;config',        # 包含配置文件
        '--add-data=public;public',        # 包含资源文件
        '--hidden-import=paddle',          # 隐式导入PaddleOCR
        '--hidden-import=cv2',             # 隐式导入OpenCV
        '--icon=public/logo.ico',          # 应用图标
        '--distpath=release'               # 输出目录
    ])
  
    print("主应用程序构建完成！")

def build_updater():
    """构建更新器程序"""
    print("正在构建更新器程序...")
  
    PyInstaller.__main__.run([
        'updater.py',                      # 更新器源码
        '--name=updater',                  # 生成的exe名称
        '--console',                       # 显示控制台（显示更新进度）
        '--onefile',                       # 单个exe文件
        '--distpath=release'               # 输出到同一目录
    ])
  
    print("更新器程序构建完成！")

def create_release_structure():
    """创建发布目录结构"""
    print("创建发布目录结构...")
  
    release_dir = Path("release")
  
    # 创建必要的目录
    (release_dir / "config").mkdir(exist_ok=True)
    (release_dir / "data").mkdir(exist_ok=True)
    (release_dir / "temp").mkdir(exist_ok=True)
  
    # 复制配置文件
    if os.path.exists("config/update_config.json"):
        shutil.copy2("config/update_config.json", release_dir / "config/")
  
    # 复制版本文件
    if os.path.exists("version.txt"):
        shutil.copy2("version.txt", release_dir / "version.txt")
  
    print("发布目录结构创建完成！")

def main():
    """主构建流程"""
    print("开始构建Kuzflow应用程序...")
  
    # 1. 清理旧文件
    clean_build()
  
    # 2. 构建主程序
    build_main_app()
  
    # 3. 构建更新器
    build_updater()
  
    # 4. 创建发布结构
    create_release_structure()
  
    print("\n" + "=" * 50)
    print("构建完成！")
    print("发布文件在 release/ 目录下：")
    print("  - KuzflowApp.exe  (主程序)")
    print("  - updater.exe     (更新器)")
    print("  - config/         (配置文件)")
    print("  - data/           (数据目录)")
    print("  - temp/           (临时目录)")
    print("=" * 50)

if __name__ == "__main__":
    main()
```

## 🌐 服务端修改

你的服务端需要支持exe文件下载，修改 `server/start.py`：

```python
@app.get("/api/version/download/{version}")
async def download_version(version: str):
    """下载exe文件版本"""
    try:
        # exe文件路径
        exe_path = f"releases/v{version}/KuzflowApp.exe"
      
        if not os.path.exists(exe_path):
            raise HTTPException(status_code=404, detail="exe文件不存在")
      
        return FileResponse(
            exe_path,
            media_type='application/octet-stream',
            filename=f"KuzflowApp_v{version}.exe"
        )
      
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@app.get("/api/version/check")
async def check_version(current_version: str = Query(...)):
    """检查版本（返回exe下载链接）"""
    # ... 原有逻辑 ...
  
    return {
        "update_available": True,
        "latest_version": "1.1.0",
        "download_url": f"/api/version/download/1.1.0",  # 直接下载exe
        "file_size": os.path.getsize("releases/v1.1.0/KuzflowApp.exe"),
        "file_hash": calculate_file_hash("releases/v1.1.0/KuzflowApp.exe")
    }
```

## 📦 完整的使用流程

### 1. 开发阶段

```bash
# 1. 开发你的应用
python app.py

# 2. 测试更新功能
python updater.py
```

### 2. 构建阶段

```bash
# 一键构建所有文件
python build.py
```

### 3. 发布阶段

```bash
# 将 release/ 目录打包给用户
zip -r KuzflowApp_v1.0.0.zip release/
```

### 4. 用户使用

```
用户解压 → 运行 KuzflowApp.exe → 自动检查更新 → 一键更新
```

## ⚠️ 重要注意事项

### 1. 安全性

```python
# 验证下载的文件
def verify_download(file_path, expected_hash):
    # 必须验证文件哈希，防止下载损坏或被篡改
    pass
```

### 2. 错误处理

```python
# 更新失败时的回滚机制
try:
    update_process()
except Exception:
    restore_backup()  # 恢复备份
    show_error_to_user()  # 通知用户
```

### 3. 用户体验

```python
# 显示更新进度
def show_progress(percent, message):
    print(f"更新进度：{percent}% - {message}")
```

## 🎯 环境变化的处理

### 如果新版本有新的依赖：

1. **重新构建时包含新依赖**：

```bash
pyinstaller --hidden-import=新依赖包 app.py
```

2. **服务端返回更大的文件**：

```python
# 新版本的exe会包含所有新依赖
# 用户下载后直接替换即可
```

3. **检测依赖变化**：

```python
# 可以在版本信息中标记是否有依赖变化
{
    "version": "1.1.0",
    "dependencies_changed": true,  # 提示用户这是一个大更新
    "download_size": 50000000      # 50MB（包含新依赖）
}
```

## 🚀 完整示例项目结构

```
你的项目目录：
kuzflow_project/
├── app.py                  # 主应用程序
├── updater.py             # 更新器程序
├── build.py               # 构建脚本
├── config/
│   └── update_config.json
├── public/
│   └── logo.ico
├── version.txt
├── requirements.txt       # Python依赖
└── release/              # 构建后的发布文件
    ├── KuzflowApp.exe
    ├── updater.exe
    ├── config/
    ├── data/
    └── temp/
```

## 💡 小白友好提示

### Q: 我不懂编程，怎么修改这些代码？

**A**: 你只需要：

1. 把上面的代码复制到对应文件中
2. 修改几个地方的名称（比如把"KuzflowApp"改成你的应用名）
3. 运行 `python build.py` 构建

### Q: 如何测试更新功能？

**A**:

1. 先构建v1.0.0版本给用户
2. 修改代码后构建v1.1.0版本放到服务器
3. 用户运行v1.0.0，会自动检测到v1.1.0并更新

### Q: 用户电脑没有Python环境怎么办？

**A**: 没关系！PyInstaller会把所有需要的Python环境都打包进exe文件，用户不需要安装Python。

### Q: 更新失败了怎么办？

**A**: 更新器会自动备份旧版本，失败时会自动恢复，确保用户的应用不会损坏。

---

这个方案完美解决了PyInstaller打包后的在线更新问题，支持环境变化，用户体验良好！

有任何不清楚的地方，随时问我！ 😊
