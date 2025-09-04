#!/usr/bin/env python3
"""
PyInstaller在线更新流程测试脚本
模拟完整的更新过程
"""

import os
import sys
import time
import requests
import json
import subprocess
from pathlib import Path

def test_server_connection():
    """测试服务器连接"""
    print("[测试] 测试服务器连接...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code == 200:
            print("[成功] 服务器连接成功")
            return True
        else:
            print(f"[失败] 服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"[失败] 无法连接到服务器: {e}")
        return False

def test_version_check():
    """测试版本检查API"""
    print("\n[测试] 测试版本检查...")
    
    try:
        url = "http://127.0.0.1:8000/api/version/check"
        params = {
            "current_version": "1.0.0",
            "platform": "windows", 
            "arch": "x64"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("[成功] 版本检查API正常")
            print(f"   当前版本: {data.get('current_version')}")
            print(f"   最新版本: {data.get('latest_version')}")
            print(f"   有更新: {data.get('update_available')}")
            print(f"   下载URL: {data.get('download_url')}")
            print(f"   文件大小: {data.get('file_size')} 字节")
            return data
        else:
            print(f"[失败] 版本检查失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[失败] 版本检查异常: {e}")
        return None

def test_exe_download():
    """测试exe文件下载"""
    print("\n🔍 测试exe文件下载...")
    
    try:
        url = "http://127.0.0.1:8000/api/version/download_exe/1.1.0"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ exe文件下载成功")
            print(f"   文件大小: {len(response.content)} 字节")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
            # 保存到临时文件进行验证
            temp_file = "temp_download_test.exe"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # 验证文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "版本 1.1.0" in content:
                    print("✅ 下载文件内容正确")
                else:
                    print("⚠️ 下载文件内容可能有问题")
            
            # 清理临时文件
            os.remove(temp_file)
            return True
            
        else:
            print(f"❌ exe下载失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ exe下载异常: {e}")
        return False

def test_updater_exists():
    """检查更新器文件是否存在"""
    print("\n🔍 检查更新器文件...")
    
    client_dir = Path("client")
    updater_file = client_dir / "updater.py"
    
    if updater_file.exists():
        print("✅ 更新器文件存在")
        
        # 检查文件内容
        with open(updater_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "update_application" in content:
                print("✅ 更新器函数完整")
                return True
            else:
                print("❌ 更新器函数不完整")
                return False
    else:
        print(f"❌ 更新器文件不存在: {updater_file}")
        return False

def test_config_files():
    """检查配置文件"""
    print("\n🔍 检查配置文件...")
    
    config_files = [
        "client/config/update_config.json",
        "client/version.txt", 
        "server/config.json"
    ]
    
    all_ok = True
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            all_ok = False
    
    return all_ok

def simulate_update_process():
    """模拟更新过程"""
    print("\n🚀 模拟更新过程...")
    
    # 1. 创建模拟的更新信息
    update_info = {
        "update_available": True,
        "latest_version": "1.1.0",
        "download_url": "/api/version/download_exe/1.1.0",
        "file_size": 1112,
        "file_hash": "mock_hash_for_testing"
    }
    
    # 2. 保存更新信息到临时文件
    temp_dir = Path("client/temp")
    temp_dir.mkdir(exist_ok=True)
    
    update_info_file = temp_dir / "update_info_test.json"
    with open(update_info_file, 'w', encoding='utf-8') as f:
        json.dump(update_info, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 更新信息文件已创建: {update_info_file}")
    
    # 3. 模拟调用更新器（不实际执行，只检查命令）
    updater_command = [
        "python", "client/updater.py",
        str(update_info_file),
        "TestApp.exe"
    ]
    
    print(f"📝 更新器命令: {' '.join(updater_command)}")
    print("ℹ️  在实际环境中，这个命令会下载新版本并替换exe文件")
    
    # 清理测试文件
    if update_info_file.exists():
        update_info_file.unlink()
    
    return True

def test_release_files():
    """检查发布文件结构"""
    print("\n🔍 检查发布文件结构...")
    
    release_files = [
        "server/releases/v1.0.0/KuzflowApp_v1.0.0.exe",
        "server/releases/v1.1.0/KuzflowApp_v1.1.0.exe",
        "server/releases/v1.0.0/manifest.json",
        "server/releases/v1.1.0/manifest.json"
    ]
    
    all_ok = True
    for file_path in release_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({file_size} 字节)")
        else:
            print(f"❌ {file_path} 不存在")
            all_ok = False
    
    return all_ok

def main():
    """主测试函数"""
    print("=" * 60)
    print("[测试] PyInstaller在线更新系统测试")
    print("=" * 60)
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    test_results = []
    
    # 执行各项测试
    tests = [
        ("服务器连接", test_server_connection),
        ("版本检查API", test_version_check),
        ("exe文件下载", test_exe_download),
        ("更新器文件", test_updater_exists),
        ("配置文件", test_config_files),
        ("发布文件", test_release_files),
        ("模拟更新流程", simulate_update_process)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
            if result:
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"💥 {test_name} - 异常: {e}")
            test_results.append((test_name, False))
    
    # 显示测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！PyInstaller在线更新系统运行正常！")
        print("\n🚀 现在你可以:")
        print("1. 运行客户端: cd client && python app.py")
        print("2. 构建exe版本: cd client && python build.py")
        print("3. 测试完整更新流程")
    else:
        print(f"\n⚠️ 有 {total - passed} 项测试失败，请检查相关组件。")
        print("\n🔧 排查建议:")
        print("1. 确保服务端正在运行: cd server && python start.py")
        print("2. 检查网络连接和端口占用")
        print("3. 验证文件路径和权限")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)