"""
更新安装器
负责解压和安装更新包
"""

import os
import shutil
import zipfile
import tempfile
import time
from pathlib import Path


class UpdateInstaller:
    """更新安装器"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
    
    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(f"[安装器] {message}")
        else:
            print(f"[安装器] {message}")
    
    def install_update(self, package_path, install_dir, current_version, target_version):
        """
        安装更新包
        
        Args:
            package_path: 更新包文件路径
            install_dir: 安装目录
            current_version: 当前版本
            target_version: 目标版本
        
        Returns:
            bool: 安装是否成功
        """
        try:
            self.log(f"开始安装更新: {current_version} -> {target_version}")
            
            # 验证更新包
            if not self.verify_package(package_path):
                raise Exception("更新包验证失败")
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压更新包
                self.log("解压更新包...")
                if not self.extract_package(package_path, temp_path):
                    raise Exception("解压更新包失败")
                
                # 安装文件
                self.log("安装更新文件...")
                if not self.install_files(temp_path, Path(install_dir)):
                    raise Exception("安装文件失败")
            
            self.log("更新安装完成")
            return True
            
        except Exception as e:
            self.log(f"安装失败: {e}")
            return False
    
    def verify_package(self, package_path):
        """验证更新包"""
        try:
            if not os.path.exists(package_path):
                self.log("更新包文件不存在")
                return False
            
            # 检查是否为有效的zip文件
            if not zipfile.is_zipfile(package_path):
                self.log("不是有效的zip文件")
                return False
            
            # 检查zip文件内容
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # 检查必需的文件
                required_files = ['app.py']  # 至少要有主程序文件
                
                for required_file in required_files:
                    if not any(f.endswith(required_file) for f in file_list):
                        self.log(f"缺少必需文件: {required_file}")
                        return False
            
            self.log("更新包验证通过")
            return True
            
        except Exception as e:
            self.log(f"验证更新包时出错: {e}")
            return False
    
    def extract_package(self, package_path, extract_dir):
        """解压更新包"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                # 解压所有文件
                zip_ref.extractall(extract_dir)
                
                # 列出解压的文件
                extracted_files = list(extract_dir.rglob('*'))
                self.log(f"解压了 {len(extracted_files)} 个文件")
                
                return True
                
        except Exception as e:
            self.log(f"解压失败: {e}")
            return False
    
    def install_files(self, source_dir, target_dir):
        """安装文件到目标目录"""
        try:
            # 需要更新的文件模式
            update_patterns = [
                'app.py',
                'manipulate/*.py',
                'config/*.json',
                'public/*'
            ]
            
            # 需要保护的文件（不覆盖）
            protected_files = [
                'version.txt',  # 版本文件由更新管理器单独处理
                'temp/*',
                'backup/*'
            ]
            
            installed_count = 0
            
            # 遍历源目录中的所有文件
            for source_file in source_dir.rglob('*'):
                if source_file.is_file():
                    # 计算相对路径
                    rel_path = source_file.relative_to(source_dir)
                    target_file = target_dir / rel_path
                    
                    # 检查是否为受保护的文件
                    if self.is_protected_file(rel_path, protected_files):
                        self.log(f"跳过受保护文件: {rel_path}")
                        continue
                    
                    # 创建目标目录
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 复制文件
                    try:
                        shutil.copy2(source_file, target_file)
                        installed_count += 1
                        self.log(f"安装文件: {rel_path}")
                    except Exception as e:
                        self.log(f"安装文件失败 {rel_path}: {e}")
                        # 继续安装其他文件
            
            self.log(f"成功安装 {installed_count} 个文件")
            return installed_count > 0
            
        except Exception as e:
            self.log(f"安装文件时出错: {e}")
            return False
    
    def is_protected_file(self, file_path, protected_patterns):
        """检查文件是否受保护"""
        file_str = str(file_path).replace('\\', '/')
        
        for pattern in protected_patterns:
            pattern = pattern.replace('\\', '/')
            
            if '*' in pattern:
                # 简单的通配符匹配
                if pattern.endswith('/*'):
                    dir_pattern = pattern[:-2]
                    if file_str.startswith(dir_pattern + '/'):
                        return True
                elif pattern.startswith('*/'):
                    file_pattern = pattern[2:]
                    if file_str.endswith('/' + file_pattern):
                        return True
            else:
                # 精确匹配
                if file_str == pattern:
                    return True
        
        return False
    
    def create_file_manifest(self, install_dir, version):
        """创建安装清单"""
        try:
            manifest_file = Path(install_dir) / f"install_manifest_{version}.txt"
            
            with open(manifest_file, 'w', encoding='utf-8') as f:
                f.write(f"# 安装清单 - 版本 {version}\n")
                f.write(f"# 安装时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 列出所有已安装的文件
                for file_path in Path(install_dir).rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('install_manifest_'):
                        rel_path = file_path.relative_to(install_dir)
                        f.write(f"{rel_path}\n")
            
            self.log(f"创建安装清单: {manifest_file}")
            return True
            
        except Exception as e:
            self.log(f"创建安装清单失败: {e}")
            return False
    
    def verify_installation(self, install_dir, expected_files=None):
        """验证安装结果"""
        try:
            if expected_files is None:
                expected_files = ['app.py']
            
            missing_files = []
            
            for expected_file in expected_files:
                file_path = Path(install_dir) / expected_file
                if not file_path.exists():
                    missing_files.append(expected_file)
            
            if missing_files:
                self.log(f"安装验证失败，缺少文件: {missing_files}")
                return False
            
            self.log("安装验证通过")
            return True
            
        except Exception as e:
            self.log(f"验证安装时出错: {e}")
            return False
    
    def cleanup_installation(self, install_dir):
        """清理安装过程中的临时文件"""
        try:
            # 删除临时文件
            temp_patterns = ['*.tmp', '*.temp', '.DS_Store', 'Thumbs.db']
            
            cleaned_count = 0
            for pattern in temp_patterns:
                for temp_file in Path(install_dir).rglob(pattern):
                    try:
                        temp_file.unlink()
                        cleaned_count += 1
                    except Exception:
                        pass
            
            if cleaned_count > 0:
                self.log(f"清理了 {cleaned_count} 个临时文件")
            
            return True
            
        except Exception as e:
            self.log(f"清理安装时出错: {e}")
            return False
