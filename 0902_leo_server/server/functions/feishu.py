from typing import Any, Dict, List, Optional
import requests
import time
import re
import hashlib
from datetime import datetime, timezone, timedelta
try:
    # 优先使用标准库时区（Python 3.9+）
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:
    ZoneInfo = None  # 运行环境不支持时，回退到固定偏移

class FeishuService:
    def __init__(self, credentials: Dict[str, Any], table_db: Dict[str, Any], doc_db: Dict[str, Any] = None) -> None:
        """
        credentials: {
            "app_id": "...",
            "app_secret": "...",
            "app_token": "...",
            "table_id": "...",
            "auth_url": "..."
        }
        table_db: {
            "<table_name>": {
                "app_token": "...",
                "table_id": "...",
                "fields_mapping": { "字段A": "...", ... },
                "is_array_data": true/false
            }
        }
        """
        self.credentials = credentials or {}
        self.table_db = table_db or {}
        self.doc_db = doc_db or {}

    # ----------------------- Public API -----------------------

    def schedule_write(self, request: Any, background_tasks: Any) -> Dict[str, Any]:
        """
        解析请求并调度后台写入任务。
        - 支持 processed_result 为 dict/list 的解析
        - 支持表级 is_array_data 决策批量写入
        - 保持与原实现一致的字段映射与默认字段
        """
        try:
            fields: Dict[str, Any] = getattr(request, "fields", None) or {}

            processed_result = getattr(request, "processed_result", None)
            table_name = getattr(request, "table_name", None)
            source = getattr(request, "source", None)

            if not fields and processed_result:
                try:
                    parsed = self._safe_json(processed_result)
                    if isinstance(parsed, dict):
                        fields = parsed
                    elif isinstance(parsed, list):
                        table_config = self.table_db.get(table_name or "", {})
                        if table_config.get("is_array_data", False):
                            background_tasks.add_task(self.write_array_background, parsed, source, table_name)
                            return {"ok": True, "message": f"已安排写入 {len(parsed)} 条记录"}
                        else:
                            fields = parsed[0] if parsed else {}
                except Exception as e:
                    print(f"解析processed_result失败: {e}")
                    fields = {}

            feishu_fields = self.build_feishu_fields(fields, table_name)
            background_tasks.add_task(self.write_background, feishu_fields, source, table_name)
            return {"ok": True}
        except Exception as e:
            print(f"schedule_write 异常: {e}")
            return {"ok": False, "error": str(e)}

    # ----------------------- Background tasks -----------------------

    def write_array_background(self, records: List[Dict[str, Any]], source: Optional[str] = None, table_name: Optional[str] = None) -> None:
        """处理数组数据的飞书写入后台任务，逐条写入记录"""
        try:
            print(f"开始处理数组数据写入: {len(records)} 条记录，表格: {table_name}")

            success_count = 0
            failed_count = 0

            # 与原实现保持一致：特定表初始延迟
            if table_name == "抖音创作者信息2":
                initial_delay = 1.0
            else:
                initial_delay = 0.0

            if initial_delay > 0:
                print(f"表格 {table_name} 延迟 {initial_delay} 秒开始写入")
                time.sleep(initial_delay)

            for i, record in enumerate(records):
                try:
                    record_source = f"{source}_{table_name}_记录{i+1}" if source else None
                    self.write_background(record, record_source, table_name)
                    success_count += 1
                    print(f"✅ {table_name} 第 {i+1}/{len(records)} 条记录写入成功")

                    # 与原实现保持一致：不同表写入间隔
                    if table_name == "抖音创作者信息1":
                        time.sleep(0.6)
                    else:
                        time.sleep(0.8)

                except Exception as e:
                    failed_count += 1
                    print(f"❌ {table_name} 第 {i+1} 条记录写入失败: {e}")

            print(f"📊 {table_name} 数组写入完成: 成功 {success_count}/{len(records)} 条，失败 {failed_count} 条")
        except Exception as e:
            print(f"❌ {table_name} 数组数据写入异常: {e}")

    def write_background(self, fields: Dict[str, Any], source: Optional[str] = None, table_name: Optional[str] = None) -> None:
        """单条记录的飞书写入后台任务，支持防重复（查重+更新）"""
        try:
            token = self.get_tenant_access_token()
            if not token:
                print("未获取到tenant_access_token，放弃写入飞书")
                return

            table_config = self.resolve_table_config(table_name)
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]

            print(f"使用多维表格配置: {table_name} -> {table_id}" if table_name and table_name in self.table_db else f"使用默认表配置: {table_id}")

            # 按表的 fields_mapping 过滤/取值，并进行类型转换
            filtered_fields = fields
            if table_name and table_name in self.table_db:
                fields_mapping = self.table_db[table_name].get("fields_mapping", {})
                if fields_mapping:
                    filtered_fields = {}
                    for field_name, field_config in fields_mapping.items():
                        raw_value = fields.get(field_name, "")
                        converted_value = self._convert_field_value(raw_value, field_config)
                        filtered_fields[field_name] = converted_value

            # 生成主键并添加到字段中
            primary_key_field = self.table_db.get(table_name, {}).get("primary_key_field") if table_name else None
            if primary_key_field:
                primary_key_value = self._generate_primary_key(fields, table_name)
                if primary_key_value:
                    filtered_fields[primary_key_field] = primary_key_value
                    print(f"🔑 生成主键: {primary_key_field} = {primary_key_value}")
                    print(f"📝 原始数据用于哈希: {[str(fields.get(field, '')) for field in self.table_db[table_name].get('hash_fields', [])]}")
                    
                    # 查询是否存在该主键的记录
                    existing_record = self._query_existing_record(primary_key_value, table_name)
                    
                    if existing_record:
                        # 记录存在，执行更新
                        record_id = existing_record.get("record_id")
                        if record_id:
                            print(f"🔄 发现重复记录，执行更新: record_id={record_id}")
                            success = self._update_existing_record(record_id, filtered_fields, table_name)
                            if success:
                                print(f"✅ 更新飞书记录成功: table={table_name}, record_id={record_id}")
                                return
                            else:
                                print(f"❌ 更新失败，尝试删除旧记录并创建新记录")
                                # 如果更新失败，尝试删除旧记录
                                if self._delete_record(record_id, table_name):
                                    print(f"🗑️ 删除旧记录成功，将创建新记录")
                                else:
                                    print(f"❌ 删除旧记录也失败，跳过此次写入")
                                    return
                        else:
                            print("⚠️ 查询到记录但缺少record_id，将创建新记录")
                    else:
                        print(f"🆕 未发现重复记录，将创建新记录")
                else:
                    print(f"⚠️ 主键生成失败")
            else:
                print(f"⚠️ 表 {table_name} 未配置主键字段")

            # 执行新增操作
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            record_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            body = {"fields": filtered_fields}

            resp = requests.post(
                record_url,
                headers=headers,
                json=body,
                timeout=10,
            )
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            print(f"写入飞书表格返回: table={table_name}, status={resp.status_code}, data={data}")
        except Exception as e:
            print(f"写入飞书后台任务异常: {e}")

    # ----------------------- Hash and Primary Key -----------------------

    def _generate_primary_key(self, fields_data: Dict[str, Any], table_name: Optional[str]) -> str:
        """根据配置的hash_fields生成主键"""
        if not table_name or table_name not in self.table_db:
            return ""
        
        table_config = self.table_db[table_name]
        hash_fields = table_config.get("hash_fields", [])
        
        if not hash_fields:
            return ""
        
        # 构建哈希输入字符串，使用原始数据（转换前）
        hash_parts = []
        for field in hash_fields:
            value = str(fields_data.get(field, "")).strip()
            hash_parts.append(value)
        
        hash_input = "|".join(hash_parts)
        
        # 生成MD5哈希，取前16位作为主键
        hash_obj = hashlib.md5(hash_input.encode('utf-8'))
        return hash_obj.hexdigest()[:16]

    def _query_existing_record(self, primary_key_value: str, table_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """查询是否存在指定主键的记录"""
        if not table_name or table_name not in self.table_db:
            print(f"❌ 查询失败: 表名无效 table_name={table_name}")
            return None
        
        table_config = self.resolve_table_config(table_name)
        primary_key_field = self.table_db[table_name].get("primary_key_field")
        
        if not primary_key_field or not primary_key_value:
            print(f"❌ 查询失败: 主键字段或值无效 primary_key_field={primary_key_field}, primary_key_value={primary_key_value}")
            return None
        
        try:
            token = self.get_tenant_access_token()
            if not token:
                print("❌ 查询记录时未获取到token")
                return None
            
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]
            
            print(f"🔍 开始查询记录: {primary_key_field} = {primary_key_value}")
            
            # 使用飞书查询API，不使用filter，而是获取所有记录然后手动过滤
            # 因为飞书的filter语法可能有问题
            query_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            
            # 先尝试获取所有记录（分页）
            params = {"page_size": 500}  # 增加页面大小
            
            resp = requests.get(query_url, headers=headers, params=params, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                print(f"📊 查询到 {len(items)} 条记录，开始查找匹配的主键")
                
                # 手动查找匹配的记录
                for item in items:
                    fields = item.get("fields", {})
                    if fields.get(primary_key_field) == primary_key_value:
                        print(f"✅ 找到匹配记录: record_id={item.get('record_id')}")
                        return item
                
                print(f"🔍 未找到匹配的记录: {primary_key_field} = {primary_key_value}")
                return None
            else:
                print(f"❌ 查询记录失败: status={resp.status_code}, response={resp.text}")
        
        except Exception as e:
            print(f"❌ 查询记录异常: {e}")
        
        return None

    def _update_existing_record(self, record_id: str, fields_data: Dict[str, Any], table_name: Optional[str]) -> bool:
        """更新现有记录"""
        try:
            token = self.get_tenant_access_token()
            if not token:
                print("❌ 更新记录时未获取到token")
                return False
            
            table_config = self.resolve_table_config(table_name)
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]
            
            print(f"🔄 开始更新记录: record_id={record_id}, table={table_name}")
            
            # 使用飞书更新API - 尝试PUT方法
            update_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            
            body = {"fields": fields_data}
            print(f"📤 更新请求: URL={update_url}")
            print(f"📤 更新数据: {body}")
            
            # 先尝试PUT方法
            resp = requests.put(update_url, headers=headers, json=body, timeout=10)
            
            if resp.status_code == 200:
                print(f"✅ 更新记录成功(PUT): record_id={record_id}, table={table_name}")
                return True
            elif resp.status_code == 404:
                print(f"⚠️ PUT方法404，尝试PATCH方法")
                # 如果PUT失败，尝试PATCH
                resp = requests.patch(update_url, headers=headers, json=body, timeout=10)
                if resp.status_code == 200:
                    print(f"✅ 更新记录成功(PATCH): record_id={record_id}, table={table_name}")
                    return True
                else:
                    print(f"❌ PATCH更新失败: status={resp.status_code}, response={resp.text}")
                    return False
            else:
                print(f"❌ PUT更新失败: status={resp.status_code}, response={resp.text}")
                return False
        
        except Exception as e:
            print(f"❌ 更新记录异常: {e}")
            return False

    def _delete_record(self, record_id: str, table_name: Optional[str]) -> bool:
        """删除指定记录"""
        try:
            token = self.get_tenant_access_token()
            if not token:
                print("❌ 删除记录时未获取到token")
                return False
            
            table_config = self.resolve_table_config(table_name)
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]
            
            print(f"🗑️ 开始删除记录: record_id={record_id}, table={table_name}")
            
            # 使用飞书删除API
            delete_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            
            resp = requests.delete(delete_url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                print(f"✅ 删除记录成功: record_id={record_id}, table={table_name}")
                return True
            else:
                print(f"❌ 删除记录失败: status={resp.status_code}, response={resp.text}")
                return False
        
        except Exception as e:
            print(f"❌ 删除记录异常: {e}")
            return False

    # ----------------------- Data Type Conversion -----------------------

    def _convert_field_value(self, value: Any, field_config: Dict[str, Any]) -> Any:
        """根据字段配置转换数据类型"""
        if not isinstance(field_config, dict):
            # 兼容旧格式：直接是字符串的field_name
            return str(value)
        
        field_type = field_config.get("type", "string")

        # 若该字段为空，且声明了默认“台湾时间”，则注入当前台湾时间（到秒）
        try:
            is_empty = (value is None) or (isinstance(value, str) and value.strip() == "")
        except Exception:
            is_empty = value in (None, "")

        if is_empty:
            default_marker = str(field_config.get("default", "")).strip().lower() if "default" in field_config else ""
            default_now_tw = bool(field_config.get("default_now_tw", False))
            if default_now_tw or default_marker in {"now_tw", "now_tw_ms", "now_tw_string", "now_tw_iso"}:
                # 到秒：date 类型优先返回毫秒时间戳；string 类型返回格式化字符串
                if field_type == "date" or default_marker == "now_tw_ms":
                    ts_ms = self._now_in_taipei_ms()
                    print(f"⏱️ 字段默认注入台湾时间(毫秒): {ts_ms}")
                    return ts_ms
                if default_marker == "now_tw_iso":
                    iso_str = self._now_in_taipei_iso()
                    print(f"⏱️ 字段默认注入台湾时间(ISO): {iso_str}")
                    return iso_str
                # 其余情况返回可读字符串（含秒）
                str_val = self._now_in_taipei_string()
                print(f"⏱️ 字段默认注入台湾时间(字符串): {str_val}")
                return str_val
        
        if field_type == "string":
            return str(value)
        elif field_type == "int":
            # 兼容性增强：当配置为int但实际值是百分比字符串时，按百分比比值解析
            try:
                if isinstance(value, str) and ("%" in value or "％" in value):
                    # 例如 "21.82%" -> 0.2182
                    return self._convert_to_percent(value, as_ratio=True)
            except Exception:
                pass
            return self._convert_to_int(value)
        elif field_type == "percent":
            # 将百分数字符串（如"21.82%"/"0.74%"）转换为比值小数（0.2182/0.0074）
            # 也兼容不带%但语义为百分比的数值：大于1则按百分值除以100，小于等于1视为已是比值
            return self._convert_to_percent(value, as_ratio=True)
        elif field_type == "date":
            date_format = field_config.get("date_format", "yyyy/MM/dd HH:mm")
            return self._convert_to_date(value, date_format)
        else:
            return str(value)

    # ----------------------- Time Helpers (Asia/Taipei) -----------------------

    def _now_in_taipei_dt(self) -> datetime:
        """
        获取当前台湾时间（Asia/Taipei），精确到秒（去掉微秒）。
        优先使用 ZoneInfo，若不支持则回退到固定 UTC+8 偏移。
        """
        try:
            tz = ZoneInfo("Asia/Taipei") if ZoneInfo is not None else timezone(timedelta(hours=8))
        except Exception:
            tz = timezone(timedelta(hours=8))
        return datetime.now(tz=tz).replace(microsecond=0)

    def _now_in_taipei_ms(self) -> int:
        """返回台湾时间对应的 Unix 时间戳（毫秒）。"""
        return int(self._now_in_taipei_dt().timestamp() * 1000)

    def _now_in_taipei_string(self, fmt: str = "%Y/%m/%d %H:%M:%S") -> str:
        """返回台湾时间的格式化字符串，默认格式 YYYY/MM/DD HH:MM:SS。"""
        return self._now_in_taipei_dt().strftime(fmt)

    def _now_in_taipei_iso(self) -> str:
        """返回台湾时间的 ISO8601 字符串。"""
        return self._now_in_taipei_dt().isoformat()
    
    def _convert_to_int(self, value: Any) -> int:
        """将字符串数字转换为整数，支持万、亿等单位"""
        if isinstance(value, (int, float)):
            return int(value)
        
        str_value = str(value).strip()
        if not str_value:
            return 0
        
        # 处理带单位的数字：如 "10.5万" -> 105000
        if "万" in str_value:
            number_part = str_value.replace("万", "").strip()
            try:
                return int(float(number_part) * 10000)
            except ValueError:
                pass
        elif "亿" in str_value:
            number_part = str_value.replace("亿", "").strip()
            try:
                return int(float(number_part) * 100000000)
            except ValueError:
                pass
        elif "k" in str_value.lower():
            number_part = str_value.lower().replace("k", "").strip()
            try:
                return int(float(number_part) * 1000)
            except ValueError:
                pass
        
        # 移除逗号分隔符
        str_value = str_value.replace(",", "")
        
        # 直接转换数字
        try:
            return int(float(str_value))
        except ValueError:
            print(f"无法转换为整数: {value}, 使用默认值 0")
            return 0
    
    def _convert_to_date(self, value: Any, target_format: str) -> int:
        """将日期字符串转换为Unix时间戳（毫秒）"""
        # 1) 数值类型：直接按 epoch（秒/毫秒）处理
        if isinstance(value, (int, float)):
            try:
                # 小于等于0 直接视为无效
                if value <= 0:
                    return 0
                # 大于等于 10^12 视为毫秒，否则视为秒
                return int(value) if value >= 1_000_000_000_000 else int(value * 1000)
            except Exception:
                return 0

        # 2) 字符串处理
        str_value = str(value).strip()
        if not str_value:
            return 0

        # 2.1) 纯数字字符串：按 epoch（秒/毫秒）处理
        if re.fullmatch(r"\d{9,16}", str_value):
            try:
                num = int(str_value)
                return num if num >= 1_000_000_000_000 else num * 1000
            except Exception:
                pass
        
        # 匹配中文日期格式：2025年06月30日 11:00
        chinese_date_pattern = r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})"
        match = re.match(chinese_date_pattern, str_value)
        
        if match:
            year, month, day, hour, minute = match.groups()
            try:
                # 构造datetime对象
                dt = datetime(
                    year=int(year),
                    month=int(month),
                    day=int(day),
                    hour=int(hour),
                    minute=int(minute)
                )
                # 转换为Unix时间戳（毫秒）
                timestamp_ms = int(dt.timestamp() * 1000)
                return timestamp_ms
            except ValueError as e:
                print(f"日期转换失败: {str_value}, 错误: {e}")
                return 0
        
        # 如果匹配失败，尝试其他常见格式
        try:
            # 尝试解析 YYYY/MM/DD HH:MM 格式
            if "/" in str_value and ":" in str_value:
                dt = datetime.strptime(str_value, "%Y/%m/%d %H:%M")
                return int(dt.timestamp() * 1000)
            # 新增：尝试解析 YYYY-MM-DD HH:MM 格式
            elif "-" in str_value and ":" in str_value:
                dt = datetime.strptime(str_value, "%Y-%m-%d %H:%M")
                return int(dt.timestamp() * 1000)
            # 新增：尝试 ISO8601
            elif "T" in str_value:
                try:
                    # 尝试从 ISO8601 解析（不强依赖fromisoformat的时区语义）
                    dt = datetime.fromisoformat(str_value.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except Exception:
                    pass
        except ValueError:
            pass
        
        print(f"无法解析日期格式: {str_value}, 使用默认值 0")
        return 0

    def _convert_to_percent(self, value: Any, as_ratio: bool = True) -> float:
        """
        将百分比形式的值转换为浮点数。
        - 支持字符串："21.82%"、"0.74%"、"21.82"、"0.74"、包含逗号和空格；"-"或空返回0
        - 支持数值：int/float
        - as_ratio=True: 返回比值（21.82% -> 0.2182；0.74% -> 0.0074）
          若无%且值>1，则视为百分值并/100；若<=1则视为已是比值
        """
        try:
            # 数值类型直接处理
            if isinstance(value, (int, float)):
                num = float(value)
                if as_ratio:
                    return num / 100.0 if abs(num) > 1.0 else num
                return num

            s = str(value).strip()
            if not s or s in {"-", "—"}:
                return 0.0

            # 归一化：去逗号、中文百分号
            s_norm = s.replace(",", "").replace("％", "%").lower()

            has_percent = "%" in s_norm
            if has_percent:
                s_norm = s_norm.replace("%", "").strip()

            # 提取数值
            try:
                num = float(s_norm)
            except Exception:
                # 尝试用正则提取第一个数字片段
                import re
                m = re.search(r"-?\d+(?:\.\d+)?", s_norm)
                if not m:
                    return 0.0
                num = float(m.group(0))

            if as_ratio:
                if has_percent or abs(num) > 1.0:
                    return num / 100.0
                return num
            else:
                # 保留百分值（如21.82），不除以100
                return num
        except Exception:
            return 0.0

    # ----------------------- Internals -----------------------

    def get_tenant_access_token(self) -> Optional[str]:
        """根据 credentials 获取 tenant_access_token"""
        try:
            auth_url = self.credentials.get("auth_url", "")
            app_id = self.credentials.get("app_id", "")
            app_secret = self.credentials.get("app_secret", "")
            resp = requests.post(
                auth_url,
                json={"app_id": app_id, "app_secret": app_secret},
                timeout=10,
            )
            data = resp.json() if resp is not None else {}
            if resp.status_code == 200 and data.get("code", 0) == 0:
                return data.get("tenant_access_token")
            print(f"获取tenant_access_token失败: status={resp.status_code}, data={data}")
        except Exception as e:
            print(f"获取tenant_access_token异常: {e}")
        return None

    def build_feishu_fields(self, fields: Dict[str, Any], table_name: Optional[str]) -> Dict[str, Any]:
        """按表配置或默认字段生成飞书字段，支持数据类型转换和主键生成"""
        if table_name and table_name in self.table_db:
            fields_mapping = self.table_db[table_name].get("fields_mapping", {})
            feishu_fields: Dict[str, Any] = {}
            for field_name, field_config in fields_mapping.items():
                raw_value = fields.get(field_name, "")
                converted_value = self._convert_field_value(raw_value, field_config)
                feishu_fields[field_name] = converted_value
            
            # 生成主键并添加到字段中
            primary_key_field = self.table_db[table_name].get("primary_key_field")
            if primary_key_field and primary_key_field in fields_mapping:
                primary_key_value = self._generate_primary_key(fields, table_name)
                if primary_key_value:
                    feishu_fields[primary_key_field] = primary_key_value
            
            return feishu_fields
        # 默认字段集（保持与原端点一致）
        return {
            "用户名称": str(fields.get("用户名称", "")),
            "粉丝数": str(fields.get("粉丝数", "")),
        }

    def resolve_table_config(self, table_name: Optional[str]) -> Dict[str, Any]:
        """解析出最终使用的 app_token 与 table_id 等"""
        if table_name and table_name in self.table_db:
            table_cfg = self.table_db[table_name]
            return {
                "app_token": table_cfg.get("app_token", self.credentials.get("app_token", "")),
                "table_id": table_cfg.get("table_id", self.credentials.get("table_id", "")),
                "fields_mapping": table_cfg.get("fields_mapping", {}),
                "is_array_data": table_cfg.get("is_array_data", False),
            }
        return {
            "app_token": self.credentials.get("app_token", ""),
            "table_id": self.credentials.get("table_id", ""),
            "fields_mapping": {},
            "is_array_data": False,
        }

    def _safe_json(self, text: str) -> Any:
        try:
            import json
            return json.loads(text)
        except Exception:
            return text

    def get_data(self, table_name: str) -> Dict[str, Any]:
        """
        从飞书表格读取数据
        """
        try:
            token = self.get_tenant_access_token()
            if not token:
                return {"ok": False, "error": "未获取到tenant_access_token"}

            table_config = self.resolve_table_config(table_name)
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            
            # 获取表格记录
            records_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            
            resp = requests.get(
                records_url,
                headers=headers,
                params={"page_size": 500},  # 最大500条记录
                timeout=10,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", {}).get("items", [])
                
                # 转换为更友好的格式
                result_data = []
                for record in records:
                    fields = record.get("fields", {})
                    result_data.append(fields)
                
                print(f"从表格 {table_name} 读取到 {len(result_data)} 条记录")
                return {
                    "ok": True, 
                    "data": result_data,
                    "count": len(result_data)
                }
            else:
                error_msg = f"读取表格失败: {resp.status_code}, {resp.text}"
                print(error_msg)
                return {"ok": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"get_data 异常: {str(e)}"
            print(error_msg)
            return {"ok": False, "error": error_msg}

    def write_doc(self, doc_name: str, content: str) -> Dict[str, Any]:
        """
        向飞书文档写入内容
        """
        try:
            token = self.get_tenant_access_token()
            if not token:
                return {"ok": False, "error": "未获取到tenant_access_token"}

            # 从doc_db获取文档配置
            if doc_name not in self.doc_db:
                return {"ok": False, "error": f"未找到文档配置: {doc_name}"}
            
            doc_config = self.doc_db[doc_name]
            doc_token = doc_config["doc_token"]

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            
            # 构建文档内容
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_content = f"\n\n--- 更新时间: {timestamp} ---\n{content}\n"
            
            # 先获取文档信息以获取document_revision_id
            doc_info_resp = requests.get(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}",
                headers=headers,
                timeout=10,
            )
            
            if doc_info_resp.status_code != 200:
                return {"ok": False, "error": f"获取文档信息失败: {doc_info_resp.status_code}"}
            
            doc_info = doc_info_resp.json()
            document_revision_id = doc_info.get("data", {}).get("document", {}).get("revision_id")
            
            if not document_revision_id:
                return {"ok": False, "error": "未获取到document_revision_id"}
            
            # 获取文档结构以获取root_block_id
            get_resp = requests.get(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks",
                headers=headers,
                timeout=10,
            )
            
            if get_resp.status_code != 200:
                return {"ok": False, "error": f"获取文档结构失败: {get_resp.status_code}"}
            
            # 获取根块ID
            doc_data = get_resp.json()
            root_block_id = None
            if "data" in doc_data and "items" in doc_data["data"]:
                for item in doc_data["data"]["items"]:
                    if item.get("block_type") == 1:  # page block
                        root_block_id = item.get("block_id")
                        break
            
            if not root_block_id:
                return {"ok": False, "error": "未找到文档根块ID"}
            
            # 使用正确的API格式和document_revision_id添加内容
            doc_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{root_block_id}/children?document_revision_id={document_revision_id}"
            
            body = {
                "index": 0,
                "children": [
                    {
                        "block_type": 2,  # 文本块
                        "text": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": formatted_content
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            resp = requests.post(
                doc_url,
                headers=headers,
                json=body,
                timeout=10,
            )
            
            if resp.status_code in [200, 201]:
                print(f"成功写入文档 {doc_name}")
                return {"ok": True, "message": f"内容已写入文档 {doc_name}"}
            else:
                error_msg = f"写入文档失败: {resp.status_code}, {resp.text}"
                print(error_msg)
                return {"ok": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"write_doc 异常: {str(e)}"
            print(error_msg)
            return {"ok": False, "error": error_msg}