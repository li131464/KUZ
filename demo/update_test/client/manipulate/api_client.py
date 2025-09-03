"""
统一的API调用客户端
基于 0902_leo_client/manipulate/api_client.py 的设计
提供对服务器API的统一调用接口
"""

import requests
import time
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:
    """API调用客户端"""

    def __init__(self, base_url="http://127.0.0.1:8000", log_callback=None):
        self.base_url = base_url
        self.log_callback = log_callback
        self.request_count = 0
        self.total_time = 0
        self.session = requests.Session()
        
        # 设置默认超时
        self.session.timeout = 30
        
        # 设置User-Agent
        self.session.headers.update({
            'User-Agent': 'UpdateTestClient/1.0.0'
        })

    def log(self, message):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[API] {message}")

    def call_api(self, endpoint, payload=None, method="GET", timeout=30, stream=False):
        """
        统一的API调用函数
        
        Args:
            endpoint: API端点，如 "/api/version/check"
            payload: 请求数据（dict）
            method: HTTP方法
            timeout: 超时时间（秒）
            stream: 是否流式下载
        
        Returns:
            (success, data): 成功标志和返回数据
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # 构建完整URL
            url = f"{self.base_url}{endpoint}"
            
            # 记录API调用日志
            self.log(f"调用API: {method} {endpoint}")
            
            # 发送请求
            if method.upper() == "GET":
                response = self.session.get(
                    url, 
                    params=payload, 
                    timeout=timeout, 
                    verify=False,
                    stream=stream
                )
            elif method.upper() == "POST":
                response = self.session.post(
                    url, 
                    json=payload, 
                    timeout=timeout, 
                    verify=False,
                    stream=stream
                )
            else:
                self.log(f"不支持的HTTP方法: {method}")
                return False, None
            
            # 记录执行时间
            elapsed = time.time() - start_time
            self.total_time += elapsed
            
            # 检查响应状态
            if response.status_code == 200:
                if stream:
                    # 流式下载，返回response对象
                    self.log(f"API调用成功: {endpoint} ({elapsed:.3f}s) [流式]")
                    return True, response
                else:
                    # 尝试解析JSON响应
                    try:
                        data = response.json()
                        self.log(f"API调用成功: {endpoint} ({elapsed:.3f}s)")
                        return True, data
                    except:
                        # 如果不是JSON，返回文本内容
                        data = response.text
                        self.log(f"API调用成功: {endpoint} ({elapsed:.3f}s) [文本]")
                        return True, data
                        
            elif response.status_code == 206:
                # 断点续传成功
                if stream:
                    self.log(f"断点续传成功: {endpoint} ({elapsed:.3f}s)")
                    return True, response
                else:
                    return True, response.content
                    
            else:
                self.log(f"API错误 {response.status_code}: {endpoint}")
                try:
                    error_data = response.json()
                    return False, error_data
                except:
                    return False, {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"API超时: {endpoint} ({elapsed:.3f}s)")
            return False, {"error": "请求超时"}
            
        except requests.exceptions.ConnectionError:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"连接错误: {endpoint}")
            return False, {"error": "无法连接到服务器"}
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.total_time += elapsed
            self.log(f"API异常: {endpoint} - {str(e)}")
            return False, {"error": str(e)}

    def check_version(self, current_version, platform="windows", arch="x64"):
        """检查版本更新"""
        payload = {
            "current_version": current_version,
            "platform": platform,
            "arch": arch
        }
        return self.call_api("/api/version/check", payload, method="GET")

    def get_version_info(self, version):
        """获取版本详细信息"""
        return self.call_api(f"/api/version/info/{version}", method="GET")

    def get_changelog(self, version):
        """获取版本更新日志"""
        return self.call_api(f"/api/version/changelog/{version}", method="GET")

    def download_version(self, version, platform="windows", arch="x64", range_header=None):
        """下载版本更新包"""
        endpoint = f"/api/version/download/{version}"
        payload = {
            "platform": platform,
            "arch": arch
        }
        
        # 如果有Range头，添加到session headers
        if range_header:
            self.session.headers.update({"Range": range_header})
        
        success, response = self.call_api(endpoint, payload, method="GET", stream=True)
        
        # 清除Range头
        if range_header and "Range" in self.session.headers:
            del self.session.headers["Range"]
        
        return success, response

    def get_server_info(self):
        """获取服务器信息"""
        return self.call_api("/", method="GET")

    def get_debug_packages(self):
        """获取调试包列表"""
        return self.call_api("/api/debug/packages", method="GET")

    def get_stats(self):
        """获取API调用统计"""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        return {
            "total_requests": self.request_count,
            "total_time": self.total_time,
            "average_time": avg_time
        }

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
