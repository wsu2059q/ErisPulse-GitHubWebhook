# ErisPulse-GitHubWebhook

GitHub Webhook 聚合器模块，支持将 GitHub 事件转发到聊天平台。

## 功能特性

- 支持多种 GitHub 事件（push、issues、pull_request、release、star、fork、workflow、issue_comment、pull_request_review）
- 交互式命令管理 Webhook 配置
- 支持群聊和私聊两种场景
- Takumi 卡片图片渲染（极简扁平设计，内嵌跳转二维码，可关闭，失败自动回退富文本）
- 智能通知策略：独立事件（首次发版、PR 新开）发「完整卡 + 文本」，更新类事件（PR 新提交、编辑、release 附件跟进）只发紧凑增量图，不再刷屏
- release 附件差量跟进：CI 迟到的附件上传只补发一张「附件更新」小卡，不重发更新日志
- 机器人评论默认忽略（github-actions[bot] 等），可按监听放行指定 bot
- 同内容自动去重，避免重复通知
- 通知文案双语（zh-CN / en，`locale` 配置）
- 按事件配置通知策略（如 workflow 仅失败时提醒）
- 签名验证（可选）
- 历史记录查询
- 多平台适配（云湖、Telegram、QQ 等）

## 安装

```bash
epsdk install GitHubWebhook
```

图片渲染依赖 [ErisPulse-Takumi](https://pypi.org/project/ErisPulse-Takumi/)，未安装时自动使用富文本发送。

## 配置

在 `config.toml` 中添加以下配置：

```toml
[GitHubWebhook]
# 外部可访问的基础地址（必填）
# 示例: http://your-domain.com 或 https://your-ip:8080
base_url = "http://localhost:8080"

# 通知文案语言（zh-CN / en），默认 zh-CN
locale = "zh-CN"

# 同仓库同事件类型的合并窗口（秒），默认 5 秒
merge_window = 5

# 对象状态保留时间（秒），默认 7 天（604800），0 表示不清理
state_ttl = 604800

# 历史记录保留时间（天），默认 7 天
history_ttl = 7

# 错误通知限流时间（秒），默认 300 秒（5分钟）
error_ratelimit = 300

# 最大历史记录数，默认 100 条
max_history_records = 100

# 卡片图片渲染，默认 true；false 时全部使用富文本发送
render_card = true
```

## 使用方法

### 1. 添加 Webhook 监听

发送命令：
```
/ghw_add
```

按照提示输入：
- 仓库名称（如：`myorg/myproject`）
- 要监听的事件（`push`、`issues`、`pr`、`release`、`star`、`fork`、`workflow`、`comment`、`review`，多个用逗号分隔）
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

### 3. 配置通知策略与渲染

发送命令：
```
/ghw_set
```

按照提示选择仓库后，可以修改：

- `render on|off|auto` —— 卡片图片渲染 开/关/跟随全局配置
- `<事件> <动作...>` —— 通知白名单，只提醒匹配的动作或结论，例如：
  - `workflow failure` —— 仅当 CI 失败时提醒（按 conclusion 匹配）
  - `issues opened,closed` —— 仅创建/关闭时提醒
  - `release published` —— 仅正式发布时提醒
- `<事件> all` —— 恢复该事件全部通知
- `<事件> mute` —— 静音该事件
- `bot allow <login,...>` —— 放行指定机器人的评论（默认忽略所有 bot 评论）
- `bot clear` —— 清空机器人放行列表
- `clear` —— 清空通知策略（恢复全部通知）

未设置策略的事件默认通知全部动作（bot 评论除外）。

## 通知策略（防刷屏）

模块按「事件 × 动作」决定展示形态，避免 PR 状态更新、release 附件上传等更新类事件重复刷屏：

| 事件 | 动作 | 卡片 | 文本 |
|------|------|------|------|
| pull_request | opened / ready_for_review / reopened | 完整卡 | 发送 |
| pull_request | synchronize（新提交） | 紧凑增量卡「+N commits」 | 只发图 |
| pull_request | edited（标题/描述修改） | 紧凑卡（显示改了什么） | 只发图 |
| pull_request | closed | 紧凑卡；已合并时附短文本 | 视 merged |
| pull_request | labeled / review_requested 等 | 跳过 | — |
| release | published / prereleased | 完整卡（更新日志 + 附件清单） | 发送 |
| release | edited（CI 补传附件 / 日志修订） | 紧凑差量卡（只列变化） | 只发图 |
| issues | opened | 完整卡 | 发送 |
| issues | closed / reopened | 紧凑卡 | 发送短文本 |
| issues | edited | 紧凑卡 | 只发图 |
| push | 推送（窗口内自动合并提交） | 完整卡 | 发送 |
| star / fork | 收藏 / 复刻 | 完整卡 | 发送 |
| workflow_run | 任意结论 | 完整卡 | 仅失败时发送 |
| issue_comment | created / edited | 紧凑卡（作者 + 摘要 + 二维码） | 只发图 |
| pull_request_review | submitted | 紧凑卡（审查人 + 结论 + 摘要） | 只发图 |

配套机制：

- **内容去重**：同一对象（同一个 PR / release）渲染内容与上次完全一致时直接跳过
- **机器人过滤**：`issue_comment` / `pull_request_review` 默认忽略 bot（`github-actions[bot]` 等），`/ghw_set` 的 `bot allow` 可放行
- **合并窗口**：同仓库同事件的连续动作在 `merge_window` 秒内合并（push 合并提交列表，release 只保留最后一条）
- **回退**：更新类事件在渲染不可用时只发一行短文本（如「PR #12 更新：+2 个提交」），不会退回全量长文

### 4. 删除监听

发送命令：
```
/ghw_remove
```

按照提示选择要删除的监听配置。

### 5. 查看历史记录

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
| pull_request | PR 打开/更新/合并/关闭 | 操作类型、PR 标题、发起者、分支信息、链接；更新类动作发紧凑增量卡 |
| release | 发布版本 | 版本号、发布者、描述、附件清单；附件迟到时补发差量小卡 |
| star | 收藏仓库 | 收藏者、仓库、Star 总数 |
| fork | 复刻仓库 | 复刻者、目标仓库 |
| workflow | 工作流运行 | 工作流名、运行序号、结论、分支、提交信息 |
| comment | Issue/PR 评论 | 评论者、评论摘要、跳转链接；bot 默认忽略 |
| review | PR 审查 | 审查人、结论（通过/请求修改/评论）、审查摘要 |

> GitHub 侧对应的事件名为 `issue_comment`、`pull_request_review`，配置 GitHub Webhook 时记得勾选。

## 卡片渲染

安装 ErisPulse-Takumi 后，事件通知默认渲染为极简扁平风格的卡片图片（白底黑字 + 单一强调色），页脚内嵌跳转原页面的二维码。独立事件在图片后附一条包含链接的短文本；更新类事件只发图，保持群里干净。发送链为：

```
渲染卡片图（完整/紧凑增量） → HTML 富文本 → Markdown → 纯文本
```

任一环节不可用（未装 Takumi、平台不支持图片、渲染失败）都会自动落到下一级，事件不会丢失。全局开关为 `render_card` 配置，单个监听可用 `/ghw_set` 中的 `render on|off|auto` 控制。二维码由 `segno` 生成（纯 Python 实现），未安装时仅省略二维码，不影响发送。

卡片文案语言由 `locale` 配置控制（`zh-CN` / `en`）。

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
4. **消息去重**：同一对象（PR / release 等）的渲染内容与上次完全一致时自动跳过，避免重复通知

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