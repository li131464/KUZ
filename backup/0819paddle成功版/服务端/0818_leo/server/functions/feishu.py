from typing import Any, Dict, List, Optional
import requests
import time

class FeishuService:
    def __init__(self, credentials: Dict[str, Any], table_db: Dict[str, Any]) -> None:
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
        """单条记录的飞书写入后台任务"""
        try:
            token = self.get_tenant_access_token()
            if not token:
                print("未获取到tenant_access_token，放弃写入飞书")
                return

            table_config = self.resolve_table_config(table_name)
            app_token = table_config["app_token"]
            table_id = table_config["table_id"]

            print(f"使用多维表格配置: {table_name} -> {table_id}" if table_name and table_name in self.table_db else f"使用默认表配置: {table_id}")

            record_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            # 按表的 fields_mapping 过滤/取值
            filtered_fields = fields
            if table_name and table_name in self.table_db:
                mapping_keys = self.table_db[table_name].get("fields_mapping", {}).keys()
                if mapping_keys:
                    filtered_fields = {k: str(fields.get(k, "")) for k in mapping_keys}

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

    def build_feishu_fields(self, fields: Dict[str, Any], table_name: Optional[str]) -> Dict[str, str]:
        """按表配置或默认字段生成飞书字段"""
        if table_name and table_name in self.table_db:
            fields_mapping = self.table_db[table_name].get("fields_mapping", {})
            feishu_fields: Dict[str, str] = {}
            for field_name in fields_mapping.keys():
                feishu_fields[field_name] = str(fields.get(field_name, ""))
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