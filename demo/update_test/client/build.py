"""
PyInstaller构建脚本 - 一键构建Kuzflow应用程序
支持主程序和更新器的完整构建流程
"""

import os
import sys
import shutil
import json
from pathlib import Path
import subprocess

# 构建配置
BUILD_CONFIG = {
    "app_name": "KuzflowApp",
    "app_version": "1.0.0",
    "app_description": "Kuzflow智能流程自动化管理平台",
    "output_dir": "release",
    "clean_before_build": True,
    "create_installer": False
}

def print_banner(title):
    """打印标题横幅"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n📋 步骤 {step_num}: {title}")
    print("-" * 40)

def clean_build_directories():
    """清理构建目录"""
    print("🧹 清理构建目录...")
    
    dirs_to_clean = [
        'build',
        'dist', 
        '__pycache__',
        'manipulate/__pycache__',
        BUILD_CONFIG["output_dir"]
    ]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  ✅ 已清理: {dir_name}")
            except Exception as e:
                print(f"  ⚠️ 清理失败: {dir_name} - {e}")
    
    print("清理完成！")

def check_dependencies():
    """检查构建依赖"""
    print("🔍 检查构建依赖...")
    
    required_packages = [
        'PyInstaller',
        'PyQt5',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.lower().replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package} - 未安装")
    
    if missing_packages:
        print(f"\n❌ 缺少必要的包: {', '.join(missing_packages)}")
        print("请运行以下命令安装：")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖检查通过！")
    return True

def create_spec_file():
    """创建PyInstaller规格文件"""
    print("📝 创建PyInstaller规格文件...")
    
    # 主程序规格文件
    app_spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['{os.getcwd()}'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('public', 'public'),
        ('version.txt', '.'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'requests',
        'urllib3',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{BUILD_CONFIG["app_name"]}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='public/logo.ico' if os.path.exists('public/logo.ico') else None,
)
"""
    
    # 更新器规格文件
    updater_spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['updater.py'],
    pathex=['{os.getcwd()}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests',
        'urllib3',
        'hashlib',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台以查看更新进度
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    # 写入规格文件
    with open('app.spec', 'w', encoding='utf-8') as f:
        f.write(app_spec_content)
    print("  ✅ 创建主程序规格文件: app.spec")
    
    with open('updater.spec', 'w', encoding='utf-8') as f:
        f.write(updater_spec_content)
    print("  ✅ 创建更新器规格文件: updater.spec")

def create_version_info():
    """创建版本信息文件"""
    print("📝 创建版本信息文件...")
    
    version_parts = BUILD_CONFIG["app_version"].split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    
    version_info = f"""# UTF-8
# 版本信息文件，用于Windows exe文件

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_parts[0]}, {version_parts[1]}, {version_parts[2]}, {version_parts[3]}),
    prodvers=({version_parts[0]}, {version_parts[1]}, {version_parts[2]}, {version_parts[3]}),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Kuzflow Team'),
        StringStruct(u'FileDescription', u'{BUILD_CONFIG["app_description"]}'),
        StringStruct(u'FileVersion', u'{BUILD_CONFIG["app_version"]}'),
        StringStruct(u'InternalName', u'{BUILD_CONFIG["app_name"]}'),
        StringStruct(u'LegalCopyright', u'© 2024 Kuzflow Team'),
        StringStruct(u'OriginalFilename', u'{BUILD_CONFIG["app_name"]}.exe'),
        StringStruct(u'ProductName', u'{BUILD_CONFIG["app_name"]}'),
        StringStruct(u'ProductVersion', u'{BUILD_CONFIG["app_version"]}')]
        )
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("  ✅ 版本信息文件创建完成")

def build_with_pyinstaller(spec_file, app_name):
    """使用PyInstaller构建应用"""
    print(f"🔨 构建 {app_name}...")
    
    try:
        # 运行PyInstaller
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', spec_file]
        print(f"  执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ {app_name} 构建成功")
            return True
        else:
            print(f"  ❌ {app_name} 构建失败:")
            print(f"  错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ {app_name} 构建异常: {e}")
        return False

def create_release_structure():
    """创建发布目录结构"""
    print("📁 创建发布目录结构...")
    
    release_dir = Path(BUILD_CONFIG["output_dir"])
    release_dir.mkdir(exist_ok=True)
    
    # 创建子目录
    subdirs = ['config', 'data', 'temp', 'backup', 'logs']
    for subdir in subdirs:
        (release_dir / subdir).mkdir(exist_ok=True)
        print(f"  ✅ 创建目录: {subdir}")
    
    # 复制exe文件
    dist_dir = Path('dist')
    app_exe = dist_dir / f'{BUILD_CONFIG["app_name"]}.exe'
    updater_exe = dist_dir / 'updater.exe'
    
    if app_exe.exists():
        shutil.copy2(app_exe, release_dir / f'{BUILD_CONFIG["app_name"]}.exe')
        print(f"  ✅ 复制主程序: {BUILD_CONFIG['app_name']}.exe")
    else:
        print(f"  ❌ 主程序文件不存在: {app_exe}")
        return False
    
    if updater_exe.exists():
        shutil.copy2(updater_exe, release_dir / 'updater.exe')
        print("  ✅ 复制更新器: updater.exe")
    else:
        print(f"  ❌ 更新器文件不存在: {updater_exe}")
        return False
    
    # 复制配置文件
    if os.path.exists('config'):
        for file in Path('config').glob('*'):
            if file.is_file():
                shutil.copy2(file, release_dir / 'config' / file.name)
                print(f"  ✅ 复制配置: config/{file.name}")
    
    # 复制版本文件
    if os.path.exists('version.txt'):
        shutil.copy2('version.txt', release_dir / 'version.txt')
        print("  ✅ 复制版本文件: version.txt")
    
    # 创建启动脚本
    create_start_scripts(release_dir)
    
    return True

def create_start_scripts(release_dir):
    """创建启动脚本"""
    print("📝 创建启动脚本...")
    
    # Windows批处理文件
    bat_content = f"""@echo off
chcp 65001 > nul
title {BUILD_CONFIG["app_name"]} v{BUILD_CONFIG["app_version"]}

echo 启动 {BUILD_CONFIG["app_name"]}...
echo.

:: 检查程序文件是否存在
if not exist "{BUILD_CONFIG["app_name"]}.exe" (
    echo 错误: 找不到主程序文件 {BUILD_CONFIG["app_name"]}.exe
    pause
    exit /b 1
)

:: 创建必要的目录
if not exist "data" mkdir data
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs

:: 启动程序
"{BUILD_CONFIG["app_name"]}.exe"

:: 检查退出代码
if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)
"""
    
    bat_file = release_dir / f'启动{BUILD_CONFIG["app_name"]}.bat'
    with open(bat_file, 'w', encoding='gbk') as f:
        f.write(bat_content)
    print(f"  ✅ 创建启动脚本: {bat_file.name}")

def create_readme():
    """创建README文件"""
    print("📝 创建README文件...")
    
    readme_content = f"""# {BUILD_CONFIG["app_name"]} v{BUILD_CONFIG["app_version"]}

{BUILD_CONFIG["app_description"]}

## 🚀 快速开始

### 运行方式1: 直接运行
双击 `{BUILD_CONFIG["app_name"]}.exe` 启动应用程序

### 运行方式2: 使用启动脚本  
双击 `启动{BUILD_CONFIG["app_name"]}.bat` 启动应用程序（推荐）

## 📁 目录说明

```
{BUILD_CONFIG["app_name"]}/
├── {BUILD_CONFIG["app_name"]}.exe     # 主程序
├── updater.exe                        # 更新器程序
├── 启动{BUILD_CONFIG["app_name"]}.bat # 启动脚本
├── config/                            # 配置文件
├── data/                              # 用户数据
├── temp/                              # 临时文件
├── backup/                            # 备份文件
├── logs/                              # 日志文件
└── version.txt                        # 版本信息
```

## 🔄 在线更新

应用程序支持在线自动更新：

1. **自动检查**: 启动时会自动检查更新
2. **手动检查**: 点击"检查更新"按钮
3. **自动更新**: 发现更新时会提示用户确认
4. **安全回滚**: 更新失败时会自动恢复

## ⚠️ 注意事项

1. **防火墙设置**: 首次运行时，Windows可能会询问网络权限，请选择"允许访问"
2. **杀毒软件**: 某些杀毒软件可能会误报，请添加信任
3. **管理员权限**: 通常不需要管理员权限运行
4. **网络连接**: 更新功能需要网络连接

## 🐛 常见问题

### Q: 程序无法启动？
A: 请检查：
   - 是否有足够的磁盘空间
   - 是否被杀毒软件拦截
   - 尝试以管理员身份运行

### Q: 更新失败？
A: 请检查：
   - 网络连接是否正常
   - 防火墙是否阻止了程序访问网络
   - 尝试手动下载新版本

### Q: 程序运行缓慢？
A: 请检查：
   - 系统资源使用情况
   - 清理temp目录中的临时文件
   - 重启程序

## 📞 技术支持

- 版本: v{BUILD_CONFIG["app_version"]}
- 构建时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Python版本: {sys.version}

如有问题，请联系技术支持或查看日志文件。
"""
    
    release_dir = Path(BUILD_CONFIG["output_dir"])
    readme_file = release_dir / 'README.md'
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"  ✅ README文件创建完成")

def cleanup_build_files():
    """清理构建文件"""
    print("🧹 清理构建文件...")
    
    files_to_clean = [
        'app.spec',
        'updater.spec', 
        'version_info.txt',
        'build',
        'dist',
        '__pycache__'
    ]
    
    for item in files_to_clean:
        if os.path.exists(item):
            try:
                if os.path.isfile(item):
                    os.remove(item)
                else:
                    shutil.rmtree(item)
                print(f"  ✅ 清理: {item}")
            except Exception as e:
                print(f"  ⚠️ 清理失败: {item} - {e}")

def show_build_summary():
    """显示构建总结"""
    print_banner("构建完成")
    
    release_dir = Path(BUILD_CONFIG["output_dir"])
    
    if release_dir.exists():
        print("📦 发布文件:")
        for file in sorted(release_dir.rglob('*')):
            if file.is_file():
                size = file.stat().st_size
                size_str = f"{size:,} 字节"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                
                rel_path = file.relative_to(release_dir)
                print(f"  📄 {rel_path} ({size_str})")
        
        print(f"\n📍 发布目录: {release_dir.absolute()}")
        print(f"📏 总大小: {sum(f.stat().st_size for f in release_dir.rglob('*') if f.is_file()):,} 字节")
        
        print("\n🚀 使用方法:")
        print(f"1. 进入目录: cd {release_dir}")
        print(f"2. 运行程序: {BUILD_CONFIG['app_name']}.exe")
        print("3. 或双击启动脚本")
        
        print("\n✅ 构建成功完成！")
    else:
        print("❌ 构建失败：发布目录不存在")

def main():
    """主构建流程"""
    try:
        print_banner(f"构建 {BUILD_CONFIG['app_name']} v{BUILD_CONFIG['app_version']}")
        
        # 检查当前目录
        required_files = ['app.py', 'updater.py']
        for file in required_files:
            if not os.path.exists(file):
                print(f"❌ 缺少必要文件: {file}")
                return False
        
        # 步骤1: 清理旧文件
        if BUILD_CONFIG["clean_before_build"]:
            print_step(1, "清理构建环境")
            clean_build_directories()
        
        # 步骤2: 检查依赖
        print_step(2, "检查构建依赖")
        if not check_dependencies():
            return False
        
        # 步骤3: 创建构建文件
        print_step(3, "创建构建文件")
        create_spec_file()
        create_version_info()
        
        # 步骤4: 构建主程序
        print_step(4, "构建主程序")
        if not build_with_pyinstaller('app.spec', BUILD_CONFIG["app_name"]):
            return False
        
        # 步骤5: 构建更新器
        print_step(5, "构建更新器")  
        if not build_with_pyinstaller('updater.spec', '更新器'):
            return False
        
        # 步骤6: 创建发布结构
        print_step(6, "创建发布结构")
        if not create_release_structure():
            return False
        
        # 步骤7: 创建文档
        print_step(7, "创建使用文档")
        create_readme()
        
        # 步骤8: 清理构建文件
        print_step(8, "清理构建文件")
        cleanup_build_files()
        
        # 显示构建总结
        show_build_summary()
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n❌ 构建被用户中断")
        return False
    except Exception as e:
        print(f"\n\n❌ 构建过程中发生异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n构建失败！")
        input("按回车键退出...")
        sys.exit(1)
    else:
        print("\n构建成功！")
        input("按回车键退出...")
        sys.exit(0)