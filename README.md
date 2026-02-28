# ErisPulse-GitHubWebhook

GitHub Webhook 聚合器模块，支持将 GitHub 事件转发到聊天平台。

## 功能特性

- 支持多种 GitHub 事件（push、issues、pull_request、release、star、fork）
- 交互式命令管理 Webhook 配置
- 支持群聊和私聊两种场景
- 消息去重机制
- 签名验证（可选）
- 历史记录查询
- 多平台适配（云湖、Telegram、QQ 等）

## 安装

```bash
epsdk install GitHubWebhook
```

## 配置

在 `config.toml` 中添加以下配置：

```toml
[GitHubWebhook]
# 外部可访问的基础地址（必填）
# 示例: http://your-domain.com 或 https://your-ip:8080
base_url = "http://localhost:8080"

# 历史记录保留时间（天），默认 7 天
history_ttl = 7

# 去重标记过期时间（秒），默认 3600 秒（1小时）
dedup_ttl = 3600

# 错误通知限流时间（秒），默认 300 秒（5分钟）
error_ratelimit = 300

# 最大历史记录数，默认 100 条
max_history_records = 100
```

## 使用方法

### 1. 添加 Webhook 监听

发送命令：
```
/ghw_add
```

按照提示输入：
- 仓库名称（如：`myorg/myproject`）
- 要监听的事件（`push`、`issues`、`pr`、`release`、`star`、`fork`、`workflow`，多个用逗号分隔）
- Webhook Secret（可选，发送空格或 skip 跳过）

配置成功后会返回 Webhook URL，例如：
```
配置成功！

Webhook URL: http://localhost:8080/GitHubWebhook/github-webhook/G1001_a3f2

请在 GitHub 仓库设置中配置：
- Payload URL: 上面的 URL
- Content type: application/json
- Secret: （可选，发送空格或 skip 跳过）
- Events: 选择需要的事件类型
```

### 2. 列出所有监听

发送命令：
```
/ghw_list
```

会显示当前群组/用户配置的所有 Webhook 监听。

### 3. 删除监听

发送命令：
```
/ghw_remove
```

按照提示选择要删除的监听配置。

### 4. 查看历史记录

发送命令：
```
/ghw_history
```

按照提示选择要查看历史的仓库，会显示该仓库的最近事件记录。

## 支持的事件类型

| 事件类型 | 说明 | 显示内容 |
|---------|------|---------|
| push | 代码推送 | 仓库、分支、提交者、提交数量、提交消息预览 |
| issues | Issue 创建/编辑/关闭 | 操作类型、标题、创建者、Issue 链接 |
| pull_request | PR 打开/合并/关闭 | 操作类型、PR 标题、发起者、分支信息、链接 |
| release | 发布版本 | 版本号、发布者、描述、下载链接 |
| star | 收藏仓库 | 收藏者、仓库、Star 总数 |
| fork | 复刻仓库 | 复刻者、目标仓库 |

## GitHub 配置

### 添加 Webhook

1. 进入 GitHub 仓库设置页面
2. 点击 "Webhooks" -> "Add webhook"
3. 填写以下信息：
   - **Payload URL**: 模块返回的 Webhook URL
   - **Content type**: `application/json`
   - **Secret**: （可选）如果配置了则填写相同的密钥
   - **Events**: 选择需要监听的事件类型
4. 点击 "Add webhook" 完成配置

## 消息格式示例

### Push 事件
```
[GitHub] Push 到 myorg/myproject
分支: main
推送者: JohnDoe
提交数: 3

- feat: 添加新功能 (abc1234)
- fix: 修复bug (def5678)
- docs: 更新文档 (ghi9012)

查看对比: https://github.com/myorg/myproject/compare/abc1234...def5678
```

### Issues 事件
```
[GitHub] Issue opened
仓库: myorg/myproject
标题: 发现一个问题
操作者: JaneDoe
Issue #123: https://github.com/myorg/myproject/issues/123
```

### Pull Request 事件
```
[GitHub] Pull request opened
仓库: myorg/myproject
标题: 添加新功能
发起者: JaneDoe
分支: feature/new-feature -> main
PR #456: https://github.com/myorg/myproject/pull/456
```

## 注意事项

1. **外部访问地址**：确保 `base_url` 配置正确，且 GitHub 可以访问到该地址
2. **签名验证**：建议在公共网络环境启用签名验证以提高安全性
3. **历史记录**：历史记录会定期清理，避免占用过多存储空间
4. **消息去重**：模块会自动去重，避免重复通知

## 常见问题

### Webhook 没有收到消息？

1. 检查 GitHub Webhook 配置是否正确
2. 在 GitHub 仓库中进行真实操作（如创建 Issue、提交代码）测试
3. 查看模块日志确认是否有错误
4. 检查网络连接是否正常
5. 确认隧道服务或公网地址可被 GitHub 访问

### 如何删除所有监听？

多次使用 `/ghw_remove` 命令逐个删除，或者直接删除存储中的配置。

### 支持哪些平台？

支持所有 ErisPulse 适配器，包括但不限于：
- 云湖
- Telegram
- QQ (OneBot11)
- 邮件

## 开发者

wsu2059 <wsu2059@qq.com>

## 许可证

MIT License