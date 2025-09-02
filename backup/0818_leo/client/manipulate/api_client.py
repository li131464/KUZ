"""
统一的API调用客户端
提供对服务器API的统一调用接口
"""

import requests
import time
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class APIClient:
    """API调用客户端"""
    
    # def __init__(self, base_url="https://121.4.65.242", log_callback=None):
    def __init__(self, base_url="http://0.0.0.0", log_callback=None):
        self.base_url = base_url
        self.log_callback = log_callback
        self.request_count = 0
        self.total_time = 0
    
    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def call_api(self, endpoint, payload=None, method="POST", timeout=5):
        """
        统一的API调用函数
        
        Args:
            endpoint: API端点，如 "/api/rec/get_xy"
            payload: 请求数据（dict）
            method: HTTP方法（暂时只支持POST）
            timeout: 超时时间（秒）
        
        Returns:
            (success, data): 成功标志和返回数据
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # 构建完整URL
            url = f"{self.base_url}{endpoint}"
            
            # 记录API调用日志
            self.log(f"🌐 调用API: {endpoint}")
            
            # 发送请求（忽略SSL验证）
            if method.upper() == "POST":
                response = requests.post(url, json=payload, timeout=timeout, verify=False)
            elif method.upper() == "GET":
                response = requests.get(url, params=payload, timeout=timeout, verify=False)
            else:
                self.log(f"❌ 不支持的HTTP方法: {method}")
                return False, None
            
            # 记录执行时间
            elapsed = time.time() - start_time
            self.total_time += elapsed
            
            # 检查响应状态
            if response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    data = response.json()
                    self.log(f"✅ API调用成功: {endpoint} ({elapsed:.3f}s)")
                    return True, data
                except:
                    # 如果不是JSON，返回文本内容（如rec/rec接口）
                    data = response.text.strip('"')
                    self.log(f"✅ API调用成功: {endpoint} ({elapsed:.3f}s)")
                    return True, data
            else:
                self.log(f"❌ API错误 {response.status_code}: {endpoint}")
                return False, None
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"⏰ API超时: {endpoint} ({elapsed:.3f}s)")
            return False, None
        except requests.exceptions.ConnectionError:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"🔌 连接错误: {endpoint}")
            return False, None
        except Exception as e:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"💥 API异常: {endpoint} - {str(e)}")
            return False, None
    
    def get_process_config(self, task_name):
        """获取任务流程配置"""
        payload = {"task_name": task_name}
        success, data = self.call_api("/api/get_process", payload)
        return data if success else None
    
    def get_stats(self):
        """获取API调用统计"""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        return {
            "total_requests": self.request_count,
            "total_time": self.total_time,
            "average_time": avg_time
        }