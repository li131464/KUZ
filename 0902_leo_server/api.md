Kuzflow Server API 文档（server/start.py）

- 基础信息
  - 服务名：UI操作API服务
  - 版本：1.0.0
  - 根路径：GET /
  - 返回格式：除特别说明外，均返回 JSON

- 通用说明
  - 请求体均为 JSON（POST 接口）
  - 正常返回 HTTP 200，错误时返回 HTTP 4xx/5xx
  - 识别文本接口 /api/rec/rec 成功时返回纯文本（非 JSON）

接口总览
- GET /
- POST /api/click/xy
- POST /api/scroll
- POST /api/rec/get_xy
- POST /api/rec/rec
- POST /api/keyboard
- POST /api/llm/process
- POST /api/feishu/write
- POST /api/get_process
- POST /api/drag

1) GET /
- 用途
  - 返回服务基本信息与可用端点列表
- 输入
  - 无
- 输出（JSON）
  - message: string
  - version: string
  - endpoints: string[]（端点列表）

2) POST /api/click/xy
- 用途
  - 根据目标描述从坐标库获取点击坐标
- 输入（JSON）
  - target_description: string（必填，目标名称/描述）
  - operation_id: string（可选）
- 输出（JSON）
  - success: boolean
  - coordinates: [number, number]（点击坐标 [x, y]）
  - confidence: number（置信度）
  - message: string
  - execution_time: number（执行耗时）
- 错误返回
  - 404：未找到目标（detail 为错误信息）
  - 500：服务端错误（detail 为错误信息）

3) POST /api/scroll
- 用途
  - 根据滚动描述构建滚动参数（方向、距离等）
- 输入（JSON）
  - scroll_description: string（必填，滚动操作描述）
  - operation_id: string（可选）
- 输出（JSON）
  - success: boolean
  - scroll_params: object（滚动参数，结构由配置决定）
  - confidence: number（固定为 1.0）
  - message: string
  - execution_time: number
- 错误返回
  - 404：未匹配到滚动配置（无 detail 文本）
  - 500：服务端错误（detail 为错误信息）

4) POST /api/rec/get_xy
- 用途
  - 获取“识别目标”的截图区域（第一步：坐标窗口框选）
- 输入（JSON）
  - target_description: string（必填，识别目标描述，如“流程控制”“抖音用户信息区域”等）
  - operation_id: string（可选）
- 输出（JSON）
  - upleft: [number, number]（左上角坐标 [x, y]）
  - downright: [number, number]（右下角坐标 [x, y]）
- 错误返回
  - 404：未找到目标或配置不合法（detail 为错误信息）
  - 500：服务端错误（detail 为错误信息）
- 备注
  - 服务端会从 REC_DB（operation.json 的 rec_db）中读取该目标的识别窗口坐标

5) POST /api/rec/rec
- 用途
  - 根据截图数据和目标描述进行 OCR 文本识别（第二步）
- 输入（JSON）
  - screenshot: string（必填，base64 编码的图片）
  - target_description: string（必填，识别目标描述）
  - operation_id: string（可选）
- 输出（纯文本，非 JSON）
  - 成功时：返回识别到的文本内容（text/plain）
- 错误返回
  - 500：识别失败（JSON，detail 为“识别错误: ……”）
- 备注
  - 服务端会将 base64 图片解码并保存临时文件，动态加载 rec/ocr.py 执行识别，然后返回文本结果

6) POST /api/keyboard
- 用途
  - 生成/返回键盘操作序列（可直接指定 operations，或使用 operation_name 查库）
- 输入（JSON）
  - operation_name: string（可选，操作名）
  - operations: string[]（可选，直接指定按键序列，将优先使用）
  - operation_id: string（可选）
- 输出（JSON）
  - success: boolean
  - operation_name: string
  - operations: string[]（按键序列，如 ["cmd", "c"]）
  - has_clipboard_result: boolean（是否期望剪贴板有结果）
  - description: string（操作说明）
  - execution_time: number
  - message: string
- 错误返回
  - 404：未找到指定的操作
  - 500：服务端错误（detail 为错误信息）

7) POST /api/llm/process
- 用途
  - 调用统一的 LLM Service（包含 prompt 构建/模型调用/回退策略），处理文本
- 输入（JSON）
  - content: string（可选，输入内容）
  - prompt_name: string（可选，使用的 prompt 名）
  - operation_id: string（可选）
- 输出（JSON）
  - processed_result: string（处理后的文本）
  - execution_time: number（耗时）
- 错误返回
  - 500：服务端错误（detail 为“LLM处理错误: ……”）

8) POST /api/feishu/write
- 用途
  - 将数据写入到飞书（后端异步执行），接口立即返回调度结果
- 输入（JSON）
  - fields: object（可选，飞书表单字段）
  - processed_result: string（可选，上一步处理的结果）
  - source: string（可选，来源标识）
  - table_name: string（可选，飞书表名）
- 输出（JSON）
  - 返回 FeishuService.schedule_write 的结果（由服务实现决定）
  - 异常时：{"ok": false, "error": string}
- 错误返回
  - 500：服务端错误（以 {"ok": false, "error": "..."} 返回）

9) POST /api/get_process
- 用途
  - 根据任务名返回流程配置，并附加 total_steps 字段
- 输入（JSON）
  - task_name: string（必填）
  - operation_id: string（可选）
- 输出（JSON）
  - 将流程配置对象展开返回，并附加：
    - total_steps: number（steps 的长度）
  - 提示：流程配置结构取决于 configs/process.json 中的定义
- 错误返回
  - 404：未找到任务，detail 包含可用任务列表
  - 500：服务端错误（detail 为错误信息）
- 备注
  - 该路由在文件中被重复定义两次，逻辑相同

10) POST /api/drag
- 用途
  - 根据目标描述构建拖拽的起止坐标
- 输入（JSON）
  - target_description: string（必填，拖拽目标/区域描述）
  - operation_id: string（可选）
- 输出（JSON）
  - start_position: [number, number]（起点 [x, y]）
  - end_position: [number, number]（终点 [x, y]）
  - target_description: string
  - execution_time: number
- 错误返回
  - 500：服务端错误（detail 为错误信息）

补充说明
- 配置来源
  - 坐标与操作配置来自 server/configs/operation.json（coordinate_db、scroll_db、keyboard_operations_db、drag_db、rec_db 等）
  - LLM 相关配置来自 server/configs/llm.json
  - 流程配置来自 server/configs/process.json
  - 飞书配置来自 server/configs/feishu.json
- 返回类型差异
  - /api/rec/rec 成功时返回纯文本；其他接口均返回 JSON

        