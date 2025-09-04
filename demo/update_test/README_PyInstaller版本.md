# PyInstaller版本在线更新演示项目

## 🎯 项目简介

这是一个完整的PyInstaller在线更新演示项目，展示了如何为打包成exe的PyQt5应用程序实现自动在线更新功能。

**核心特性:**
- ✅ 支持PyInstaller打包的exe文件更新
- ✅ 双程序更新模式（主程序 + 独立更新器）
- ✅ 完整的下载、备份、回滚机制
- ✅ 支持环境依赖变化
- ✅ 断点续传和文件校验
- ✅ 用户友好的更新体验

## 🏗️ 项目架构

```
update_test/
├── client/                          # 客户端（PyQt5应用）
│   ├── app.py                      # 主应用程序（已修改支持PyInstaller更新）
│   ├── updater.py                  # 独立更新器程序
│   ├── build.py                    # PyInstaller构建脚本
│   ├── manipulate/                 # 业务逻辑模块
│   ├── config/                     # 配置文件
│   └── version.txt                 # 版本号文件
├── server/                         # 服务端（FastAPI）
│   ├── start.py                    # API服务器（已修改支持exe下载）
│   ├── functions/                  # 功能模块
│   ├── releases/                   # 发布包存储
│   │   ├── v1.0.0/                # v1.0.0发布包
│   │   │   ├── KuzflowApp_v1.0.0.exe
│   │   │   └── manifest.json
│   │   └── v1.1.0/                # v1.1.0发布包  
│   │       ├── KuzflowApp_v1.1.0.exe
│   │       └── manifest.json
│   └── config.json                 # 服务器配置
└── README_PyInstaller版本.md       # 本说明文档
```

## 🚀 快速开始

### 第一步：启动服务端

```bash
cd server
python start.py
```

服务端将在 `http://127.0.0.1:8000` 运行

### 第二步：开发环境测试

```bash
cd client
python app.py
```

应用会启动并自动检查更新，你会看到从v1.0.0到v1.1.0的更新提示。

### 第三步：构建exe版本（可选）

```bash
cd client
python build.py
```

这会生成完整的可发布版本，包括：
- KuzflowApp.exe（主程序）
- updater.exe（更新器）
- 完整的目录结构

## 🔄 更新流程演示

### 场景1：开发环境测试
1. 运行 `python app.py`
2. 应用启动后会自动检查更新
3. 发现v1.1.0版本，提示用户更新
4. 点击"立即更新"会启动更新器
5. 更新器下载新版本并替换程序

### 场景2：exe版本测试
1. 构建两个版本的exe文件
2. 运行v1.0.0的KuzflowApp.exe
3. 应用检测到v1.1.0更新
4. 启动updater.exe进行更新
5. 更新完成后重启新版本

## 📋 详细操作指南

### 1. 服务端配置

**配置文件位置**: `server/config.json`

```json
{
  "versions": {
    "latest": "1.1.0",              // 最新版本
    "supported": ["1.0.0", "1.1.0"], // 支持的版本
    "force_update_from": "1.0.0"     // 强制更新的起始版本
  }
}
```

### 2. 客户端配置

**配置文件位置**: `client/config/update_config.json`

```json
{
  "update_server": {
    "base_url": "http://127.0.0.1:8000"  // 服务器地址
  },
  "check_settings": {
    "auto_check": true,                   // 启动时自动检查
    "check_on_startup": true
  }
}
```

### 3. 版本管理

**版本号文件**: `client/version.txt`
- 当前版本默认为 `1.0.0`
- 更新后会自动改为 `1.1.0`

### 4. 构建配置

**构建脚本**: `client/build.py`
- 自动构建主程序和更新器
- 创建完整的发布目录结构
- 生成启动脚本和说明文档

## 🔧 技术实现详解

### 双程序更新架构

**主程序 (app.py)**:
- 检查更新
- 启动更新器
- 自身退出释放文件锁

**更新器 (updater.py)**:
- 下载新版本exe
- 备份旧版本
- 替换主程序文件
- 启动新版本

### 服务端API

**主要接口**:
- `GET /api/version/check` - 检查版本更新
- `GET /api/version/download_exe/{version}` - 下载exe文件
- `GET /api/version/changelog/{version}` - 获取更新日志

### 安全机制

**文件完整性验证**:
- SHA256哈希校验
- 文件大小验证
- 下载完整性检查

**错误处理**:
- 自动备份旧版本
- 更新失败自动回滚
- 详细的错误日志

## 🧪 测试场景

### 测试场景1: 正常更新流程
1. ✅ 启动v1.0.0版本
2. ✅ 自动检测到v1.1.0更新
3. ✅ 用户确认更新
4. ✅ 下载新版本exe
5. ✅ 备份旧版本
6. ✅ 替换exe文件
7. ✅ 启动新版本

### 测试场景2: 断点续传
1. ✅ 开始下载大文件
2. ✅ 中断网络连接
3. ✅ 重新连接网络
4. ✅ 继续下载（支持Range请求）

### 测试场景3: 更新失败回滚
1. ✅ 下载完成但文件损坏
2. ✅ 更新器检测到问题
3. ✅ 自动回滚到备份版本
4. ✅ 显示错误信息

### 测试场景4: 网络异常处理
1. ✅ 无网络连接时的提示
2. ✅ 服务器不可达时的重试
3. ✅ 下载超时的处理

## 📝 开发者指南

### 添加新版本的步骤

1. **修改应用代码**
```bash
# 修改 app.py 中的功能
# 更新 version.txt 文件
```

2. **构建新版本**
```bash
cd client
python build.py
```

3. **部署到服务器**
```bash
# 将新的exe文件放到 server/releases/v{版本}/
# 更新 server/config.json 中的版本信息
```

### 自定义配置

**修改应用名称**:
```python
# 在 build.py 中修改
BUILD_CONFIG = {
    "app_name": "YourAppName",  # 改为你的应用名
    "app_version": "1.0.0"
}
```

**修改服务器地址**:
```json
// 在 client/config/update_config.json 中修改
{
  "update_server": {
    "base_url": "http://your-server.com:8000"
  }
}
```

## ❓ 常见问题

### Q: 为什么需要两个exe文件？
**A**: 因为正在运行的exe无法自我替换（被Windows锁定），所以需要独立的更新器来替换主程序。

### Q: 支持多平台吗？
**A**: 当前演示主要针对Windows，但架构支持扩展到Linux/macOS，只需要适配平台相关的部分。

### Q: 如何处理依赖变化？
**A**: PyInstaller会将所有依赖打包到exe中，所以新版本的exe包含新依赖，直接替换即可。

### Q: 更新包很大怎么办？
**A**: 
- 支持断点续传，网络中断后可继续下载
- 可以考虑差分更新（需要额外实现）
- 可以压缩exe文件（如UPX压缩）

### Q: 如何确保更新安全性？
**A**:
- 文件SHA256校验
- HTTPS传输（生产环境）
- 数字签名（可选，需要代码签名证书）

### Q: 用户数据会丢失吗？
**A**: 不会。用户数据存储在独立的data目录，更新只替换exe文件。

## 🚧 进阶功能

### 灰度发布
可以扩展服务端支持：
- 按用户ID分批发布
- AB测试功能
- 版本回退功能

### 增量更新
对于大型应用，可以实现：
- 二进制差分更新
- 模块化更新
- 热补丁功能

### 监控和统计
- 更新成功率统计
- 用户版本分布
- 更新性能监控

## 📞 技术支持

如果在使用过程中遇到问题：

1. **查看日志文件**:
   - 客户端: `updater.log`
   - 服务端: 控制台输出

2. **检查配置文件**:
   - 服务器地址是否正确
   - 版本号设置是否正确

3. **网络连接测试**:
   ```bash
   curl http://127.0.0.1:8000/api/version/check?current_version=1.0.0
   ```

## 🎉 总结

这个PyInstaller在线更新方案提供了：

✅ **完整的解决方案** - 从开发到部署的全流程支持
✅ **生产级特性** - 错误处理、备份回滚、安全验证
✅ **用户友好** - 自动检查、进度显示、无感知更新
✅ **开发友好** - 一键构建、详细文档、易于扩展

**这是一个可以直接用于生产环境的完整更新系统！**

---

🚀 **现在你可以开始测试完整的PyInstaller在线更新流程了！**