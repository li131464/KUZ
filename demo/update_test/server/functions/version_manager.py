"""
版本管理器
负责版本比较、更新类型判断等功能
"""

import re
from typing import Dict, Any, Optional


class VersionManager:
    """版本管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def parse_version(self, version_str: str) -> tuple:
        """解析版本号为可比较的元组"""
        # 移除 'v' 前缀（如果有的话）
        version_str = version_str.lstrip('v')
        
        # 使用正则表达式解析版本号
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.?(\d+)?)?(?:\+(.+))?$', version_str)
        
        if not match:
            # 简单版本号格式 (如 1.0, 1.1)
            parts = version_str.split('.')
            if len(parts) >= 2:
                try:
                    major = int(parts[0])
                    minor = int(parts[1])
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    return (major, minor, patch, '', 0)
                except ValueError:
                    pass
            
            raise ValueError(f"无效的版本号格式: {version_str}")
        
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        
        # 预发布版本处理
        pre_release = match.group(4) or ''
        pre_number = int(match.group(5)) if match.group(5) else 0
        
        return (major, minor, patch, pre_release, pre_number)
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本号
        返回值：
        -1: version1 < version2
         0: version1 == version2
         1: version1 > version2
        """
        try:
            v1 = self.parse_version(version1)
            v2 = self.parse_version(version2)
            
            # 比较主版本、次版本、修订版本
            for i in range(3):
                if v1[i] < v2[i]:
                    return -1
                elif v1[i] > v2[i]:
                    return 1
            
            # 比较预发布版本
            pre1, pre_num1 = v1[3], v1[4]
            pre2, pre_num2 = v2[3], v2[4]
            
            # 正式版本 > 预发布版本
            if not pre1 and pre2:
                return 1
            elif pre1 and not pre2:
                return -1
            elif pre1 and pre2:
                # 两个都是预发布版本
                if pre1 != pre2:
                    # 按字母序比较预发布类型
                    return -1 if pre1 < pre2 else 1
                else:
                    # 同类型预发布版本，比较数字
                    return -1 if pre_num1 < pre_num2 else (1 if pre_num1 > pre_num2 else 0)
            
            return 0
            
        except ValueError as e:
            print(f"版本比较错误: {e}")
            # 如果解析失败，按字符串比较
            return -1 if version1 < version2 else (1 if version1 > version2 else 0)
    
    def get_update_type(self, current_version: str, target_version: str) -> str:
        """
        确定更新类型
        返回: major, minor, patch
        """
        try:
            current = self.parse_version(current_version)
            target = self.parse_version(target_version)
            
            if current[0] != target[0]:
                return "major"
            elif current[1] != target[1]:
                return "minor"
            else:
                return "patch"
                
        except ValueError:
            return "unknown"
    
    def is_force_update_required(self, current_version: str) -> bool:
        """判断是否需要强制更新"""
        force_from = self.config["versions"].get("force_update_from", "0.0.0")
        
        try:
            return self.compare_versions(current_version, force_from) <= 0
        except:
            return False
    
    def get_version_details(self, version: str) -> Dict[str, Any]:
        """获取版本详细信息"""
        
        # 模拟版本详细信息
        version_details = {
            "1.0.0": {
                "version": "1.0.0",
                "release_date": "2024-09-01T10:00:00Z",
                "description": "初始版本",
                "features": [
                    "基本的PyQt5界面",
                    "简单的计数器功能",
                    "版本显示功能"
                ],
                "size": "2.5 MB",
                "compatibility": ["Windows", "macOS", "Linux"]
            },
            "1.1.0": {
                "version": "1.1.0", 
                "release_date": "2024-09-03T10:00:00Z",
                "description": "功能增强版本",
                "features": [
                    "新增计数器减法功能",
                    "UI主题颜色更新",
                    "添加关于对话框",
                    "性能优化"
                ],
                "size": "2.8 MB",
                "compatibility": ["Windows", "macOS", "Linux"],
                "changes": [
                    "🎨 UI颜色主题从蓝色改为绿色",
                    "➕ 新增计数器-1按钮",
                    "ℹ️ 添加关于对话框显示版本信息",
                    "🚀 优化应用启动速度"
                ]
            }
        }
        
        return version_details.get(version, {
            "version": version,
            "release_date": "2024-09-03T10:00:00Z",
            "description": f"版本 {version}",
            "features": [],
            "size": "未知",
            "compatibility": ["Windows"]
        })
    
    def get_changelog(self, version: str) -> str:
        """获取版本更新日志"""
        
        changelogs = {
            "1.0.0": """
# 版本 1.0.0 更新日志

## 🎉 初始发布

### 新功能
- ✨ 基本的PyQt5图形界面
- 🔢 简单的计数器功能（点击+1）
- 📋 版本号显示
- 🔄 检查更新功能

### 技术特性
- 🖥️ 跨平台支持（Windows/macOS/Linux）
- 🎨 现代化UI设计
- ⚡ 快速启动

### 系统要求
- Python 3.7+
- PyQt5
- 操作系统：Windows 10+, macOS 10.14+, Ubuntu 18.04+
            """,
            
            "1.1.0": """
# 版本 1.1.0 更新日志

## 🚀 功能增强版本

### 新功能
- ➕ 新增计数器减法功能（-1按钮）
- ℹ️ 添加"关于"对话框
- 🎨 UI主题颜色更新（蓝色→绿色）

### 改进
- ⚡ 优化应用启动速度
- 🔧 改进错误处理机制
- 📱 更好的响应式布局

### 修复
- 🐛 修复计数器显示问题
- 🔄 修复更新检查偶尔失败的问题

### 技术更新
- 📦 更新依赖包版本
- 🛡️ 增强安全性
- 📊 添加使用统计

### 兼容性
- ✅ 完全兼容 v1.0.0 数据
- 🔄 支持从 v1.0.0 无缝升级
            """
        }
        
        return changelogs.get(version, f"版本 {version} 的更新日志")
