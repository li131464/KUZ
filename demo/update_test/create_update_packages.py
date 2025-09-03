"""
创建更新包的脚本
用于生成v1.0.0和v1.1.0的更新包
"""

import os
import zipfile
import shutil
import json
import hashlib
from pathlib import Path


def calculate_file_hash(file_path):
    """计算文件SHA256哈希"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def create_update_package(version, source_files, output_dir):
    """创建更新包"""
    print(f"创建 v{version} 更新包...")
    
    # 创建输出目录
    version_dir = Path(output_dir) / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # 更新包文件名
    package_name = f"update_v{version}.zip"
    package_path = version_dir / package_name
    
    # 创建zip文件
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for source_file, archive_name in source_files.items():
            if Path(source_file).exists():
                zipf.write(source_file, archive_name)
                print(f"  添加文件: {archive_name}")
            else:
                print(f"  警告: 文件不存在 {source_file}")
    
    # 计算文件信息
    file_size = package_path.stat().st_size
    file_hash = calculate_file_hash(package_path)
    
    # 创建清单文件
    manifest = {
        "version": version,
        "package": {
            "filename": package_name,
            "size": file_size,
            "hash": file_hash,
            "download_url": f"/api/version/download/{version}"
        },
        "metadata": {
            "release_date": "2024-09-03T10:00:00Z",
            "platform": "windows",
            "arch": "x64"
        },
        "files": list(source_files.values())
    }
    
    manifest_path = version_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"  包大小: {file_size:,} 字节")
    print(f"  文件哈希: {file_hash}")
    print(f"  创建完成: {package_path}")
    print(f"  清单文件: {manifest_path}")
    
    return package_path, file_size, file_hash


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 创建更新包")
    print("=" * 60)
    
    # 项目根目录
    project_root = Path(__file__).parent
    client_dir = project_root / "client"
    server_dir = project_root / "server"
    releases_dir = server_dir / "releases"
    
    # 确保目录存在
    releases_dir.mkdir(parents=True, exist_ok=True)
    
    # v1.0.0 更新包（当前版本）
    print("\n📦 创建 v1.0.0 更新包...")
    v1_0_0_files = {
        str(client_dir / "app.py"): "app.py",
        str(client_dir / "version.txt"): "version.txt",
        str(client_dir / "manipulate" / "__init__.py"): "manipulate/__init__.py",
        str(client_dir / "manipulate" / "api_client.py"): "manipulate/api_client.py",
        str(client_dir / "manipulate" / "update_manager.py"): "manipulate/update_manager.py",
        str(client_dir / "manipulate" / "download_manager.py"): "manipulate/download_manager.py",
        str(client_dir / "manipulate" / "installer.py"): "manipulate/installer.py",
        str(client_dir / "manipulate" / "update_dialog.py"): "manipulate/update_dialog.py",
        str(client_dir / "config" / "update_config.json"): "config/update_config.json"
    }
    
    v1_0_0_package, v1_0_0_size, v1_0_0_hash = create_update_package(
        "1.0.0", 
        v1_0_0_files, 
        releases_dir
    )
    
    # v1.1.0 更新包（升级版本）
    print("\n📦 创建 v1.1.0 更新包...")
    
    # 先创建v1.1.0的版本文件
    v1_1_0_version_file = project_root / "v1.1.0_version.txt"
    with open(v1_1_0_version_file, 'w') as f:
        f.write("1.1.0")
    
    v1_1_0_files = {
        str(project_root / "v1.1.0_app.py"): "app.py",  # 使用v1.1.0版本的app.py
        str(v1_1_0_version_file): "version.txt",  # v1.1.0版本号
        str(client_dir / "manipulate" / "__init__.py"): "manipulate/__init__.py",
        str(client_dir / "manipulate" / "api_client.py"): "manipulate/api_client.py",
        str(client_dir / "manipulate" / "update_manager.py"): "manipulate/update_manager.py",
        str(client_dir / "manipulate" / "download_manager.py"): "manipulate/download_manager.py",
        str(client_dir / "manipulate" / "installer.py"): "manipulate/installer.py",
        str(client_dir / "manipulate" / "update_dialog.py"): "manipulate/update_dialog.py",
        str(client_dir / "config" / "update_config.json"): "config/update_config.json"
    }
    
    v1_1_0_package, v1_1_0_size, v1_1_0_hash = create_update_package(
        "1.1.0", 
        v1_1_0_files, 
        releases_dir
    )
    
    # 清理临时文件
    v1_1_0_version_file.unlink()
    
    print("\n" + "=" * 60)
    print("✅ 更新包创建完成!")
    print("=" * 60)
    print(f"📦 v1.0.0: {v1_0_0_size:,} 字节")
    print(f"📦 v1.1.0: {v1_1_0_size:,} 字节")
    print("\n🚀 现在可以启动服务端和客户端进行测试:")
    print("1. 启动服务端: python server/start.py")
    print("2. 启动客户端: python client/app.py")
    print("3. 客户端将自动检测到v1.1.0更新")


if __name__ == "__main__":
    main()
