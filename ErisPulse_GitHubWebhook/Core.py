import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import Request

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command

from .utils import (
    generate_uuid_short,
    verify_signature,
    format_timestamp,
    get_event_key,
)
from .handlers import (
    PushHandler,
    IssuesHandler,
    PRHandler,
    ReleaseHandler,
    StarHandler,
    ForkHandler,
)


class Main(BaseModule):
    """GitHub Webhook 聚合器模块主类"""
    
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubWebhook")
        self.storage = sdk.storage
        self.config = self._load_config()
        self.webhook_routes = {}
        
        # 事件处理器映射
        self.event_handlers = {
            'push': PushHandler,
            'issues': IssuesHandler,
            'pull_request': PRHandler,
            'release': ReleaseHandler,
            'star': StarHandler,
            'fork': ForkHandler,
        }
    
    @staticmethod
    def get_load_strategy():
        """返回模块加载策略"""
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(
            lazy_load=False,  # 需要立即加载以恢复路由
            priority=100
        )
    
    async def on_load(self, event):
        """模块加载时调用"""
        self.logger.info("模块加载中...")
        
        # 检查必要配置
        if not self.config.get('base_url'):
            self.logger.error("缺少必要配置: base_url，请在 config.toml 中配置 [GitHubWebhook]")
            return
        
        # 注册命令
        self._register_commands()
        
        # 恢复所有路由
        await self._restore_routes()
        
        # 清理过期数据
        await self._cleanup_expired_data()
        
        self.logger.info("模块加载完成")
    
    async def on_unload(self, event):
        """模块卸载时调用"""
        self.logger.info("模块卸载中...")
        self.logger.info("模块卸载完成")
    
    def _load_config(self):
        """加载模块配置"""
        config = self.sdk.config.getConfig("GitHubWebhook", {})
        
        # 设置默认值
        defaults = {
            'base_url': '',
            'history_ttl': 7,  # 天
            'dedup_ttl': 3600,  # 秒（1小时）
            'error_ratelimit': 300,  # 秒（5分钟）
            'max_history_records': 100,
        }
        
        for key, value in defaults.items():
            if key not in config or not config[key]:
                config[key] = value
        
        return config
    
    def _register_commands(self):
        """注册所有命令"""
        
        @command("ghw_add", help="添加 GitHub 仓库监听")
        async def add_command(event):
            await self._handle_add_command(event)
        
        @command("ghw_list", help="列出当前群组/用户的所有监听")
        async def list_command(event):
            await self._handle_list_command(event)
        
        @command("ghw_remove", help="删除 GitHub 仓库监听")
        async def remove_command(event):
            await self._handle_remove_command(event)
        
        @command("ghw_history", help="查看 Webhook 接收历史")
        async def history_command(event):
            await self._handle_history_command(event)
    
    # ========== 命令处理器 ==========
    
    async def _handle_add_command(self, event):
        """处理添加命令"""
        try:
            # 获取目标信息
            if event.is_group_message():
                target_id = event.get_group_id()
                target_type = "group"
            else:
                target_id = event.get_user_id()
                target_type = "user"
            
            # 获取平台信息
            platform = event.get_platform()
            
            await event.reply("请输入仓库名称（格式：username/repo）")
            
            # 等待用户输入仓库名
            repo_reply = await event.wait_reply(timeout=60)
            if not repo_reply:
                await event.reply("操作超时")
                return
            
            repo = repo_reply.get_text().strip()
            if not repo or '/' not in repo:
                await event.reply("仓库名称格式错误，应为 username/repo")
                return
            
            await event.reply(f"请选择要监听的事件（push,issues,pr,release,star,fork - 多个用逗号分隔）")
            
            # 等待用户输入事件类型
            events_reply = await event.wait_reply(timeout=60)
            if not events_reply:
                await event.reply("操作超时")
                return
            
            events_str = events_reply.get_text().strip()
            events = [e.strip().lower() for e in events_str.split(',') if e.strip()]
            
            # 验证事件类型
            valid_events = ['push', 'issues', 'pr', 'release', 'star', 'fork']
            invalid_events = [e for e in events if e not in valid_events]
            
            if invalid_events:
                await event.reply(f"无效的事件类型: {', '.join(invalid_events)}")
                return
            
            # 映射 pr 到 pull_request
            events = ['pull_request' if e == 'pr' else e for e in events]
            
            await event.reply("请输入 Webhook Secret（可选，发送空格或 skip 跳过）")
            
            # 等待用户输入密钥
            secret_reply = await event.wait_reply(timeout=60)
            if not secret_reply:
                await event.reply("操作超时")
                return
            
            webhook_secret = secret_reply.get_text().strip()
            if webhook_secret.lower() == 'skip' or webhook_secret == '':
                webhook_secret = None
            
            # 生成 UUID 和路径
            uuid_short = generate_uuid_short(4)
            webhook_path = f"/github-webhook/{target_id}_{uuid_short}"
            
            # 检查 UUID 冲突
            for _ in range(3):  # 最多重试3次
                configs = self.storage.get("github_webhook:configs", [])
                uuid_exists = any(c.get('uuid') == uuid_short for c in configs)
                
                if uuid_exists:
                    uuid_short = generate_uuid_short(4)
                    webhook_path = f"/github-webhook/{target_id}_{uuid_short}"
                else:
                    break
            
            # 构建配置
            config_data = {
                'uuid': uuid_short,
                'target_id': target_id,
                'target_type': target_type,
                'platform': platform,
                'repo': repo,
                'events': events,
                'webhook_secret': webhook_secret,
                'enabled': True,
                'created_at': int(time.time()),
            }
            
            # 保存配置
            configs = self.storage.get("github_webhook:configs", [])
            configs.append(config_data)
            self.storage.set("github_webhook:configs", configs)
            
            # 注册路由
            await self._register_route(config_data)
            
            # 生成完整 URL（实际访问路径包含模块名）
            base_url = self.config['base_url'].rstrip('/')
            full_webhook_path = f"/GitHubWebhook{webhook_path}"
            webhook_url = f"{base_url}{full_webhook_path}"
            
            # 返回配置信息
            msg = "配置成功！\n\n"
            msg += f"Webhook URL: {webhook_url}\n\n"
            msg += "请在 GitHub 仓库设置中配置：\n"
            msg += "- Payload URL: 上面的 URL\n"
            msg += "- Content type: application/json\n"
            msg += f"- Secret: {'已设置' if webhook_secret else '（可选）'}\n"
            msg += f"- Events: {', '.join(events)}\n\n"
            msg += "提示：使用 /ghw_list 查看所有配置"
            
            await event.reply(msg)
            self.logger.info(f"添加 Webhook 配置: {repo} -> {target_id}")
            
        except Exception as e:
            self.logger.error(f"添加 Webhook 配置失败: {e}", exc_info=True)
            await event.reply("添加失败，请稍后重试")
    
    async def _handle_list_command(self, event):
        """处理列表命令"""
        try:
            # 获取目标信息
            if event.is_group_message():
                target_id = event.get_group_id()
            else:
                target_id = event.get_user_id()
            
            # 获取所有配置
            configs = self.storage.get("github_webhook:configs", [])
            
            # 筛选当前目标的配置
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            # 构建列表信息
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            
            for i, config in enumerate(target_configs, 1):
                repo = config.get('repo', 'unknown')
                events = ', '.join(config.get('events', []))
                enabled = '启用' if config.get('enabled') else '禁用'
                webhook_path = f"/GitHubWebhook/github-webhook/{config['target_id']}_{config['uuid']}"
                
                msg += f"{i}. {repo}\n"
                msg += f"   监听事件: {events}\n"
                msg += f"   状态: {enabled}\n"
                msg += f"   Webhook URL: {webhook_path}\n\n"
            
            await event.reply(msg)
            
        except Exception as e:
            self.logger.error(f"列表命令失败: {e}", exc_info=True)
            await event.reply("获取列表失败，请稍后重试")
    
    async def _handle_remove_command(self, event):
        """处理删除命令"""
        try:
            # 获取目标信息
            if event.is_group_message():
                target_id = event.get_group_id()
            else:
                target_id = event.get_user_id()
            
            # 获取所有配置
            configs = self.storage.get("github_webhook:configs", [])
            
            # 筛选当前目标的配置
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            # 显示列表
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"
            
            msg += "\n请输入要删除的序号（输入 0 取消）"
            await event.reply(msg)
            
            # 等待用户选择
            reply = await event.wait_reply(timeout=60)
            if not reply:
                await event.reply("操作超时")
                return
            
            try:
                index = int(reply.get_text().strip())
                if index == 0:
                    await event.reply("已取消操作")
                    return
                
                if index < 1 or index > len(target_configs):
                    await event.reply("无效的序号")
                    return
            except ValueError:
                await event.reply("请输入有效的序号")
                return
            
            # 获取要删除的配置
            config_to_remove = target_configs[index - 1]
            repo = config_to_remove.get('repo', 'unknown')
            
            # 确认删除
            await event.reply(f"确认删除 {repo} 的监听配置吗？（y/n）")
            
            confirm_reply = await event.wait_reply(timeout=30)
            if not confirm_reply:
                await event.reply("操作超时")
                return
            
            confirm = confirm_reply.get_text().strip().lower()
            if confirm != 'y' and confirm != 'yes':
                await event.reply("已取消操作")
                return
            
            # 从配置列表中删除
            configs = [c for c in configs if c != config_to_remove]
            self.storage.set("github_webhook:configs", configs)
            
            # 注销路由
            webhook_path = f"/GitHubWebhook/github-webhook/{config_to_remove['target_id']}_{config_to_remove['uuid']}"
            if webhook_path in self.webhook_routes:
                del self.webhook_routes[webhook_path]
            
            await event.reply("删除成功！")
            self.logger.info(f"删除 Webhook 配置: {repo}")
            
        except Exception as e:
            self.logger.error(f"删除命令失败: {e}", exc_info=True)
            await event.reply("删除失败，请稍后重试")
    
    async def _handle_history_command(self, event):
        """处理历史命令"""
        try:
            # 获取目标信息
            if event.is_group_message():
                target_id = event.get_group_id()
            else:
                target_id = event.get_user_id()
            
            # 获取所有配置
            configs = self.storage.get("github_webhook:configs", [])
            
            # 筛选当前目标的配置
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            # 显示列表
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"
            
            msg += "\n请选择要查看历史的仓库（输入 0 取消）"
            await event.reply(msg)
            
            # 等待用户选择
            reply = await event.wait_reply(timeout=60)
            if not reply:
                await event.reply("操作超时")
                return
            
            try:
                index = int(reply.get_text().strip())
                if index == 0:
                    await event.reply("已取消操作")
                    return
                
                if index < 1 or index > len(target_configs):
                    await event.reply("无效的序号")
                    return
            except ValueError:
                await event.reply("请输入有效的序号")
                return
            
            # 获取选中的配置
            config = target_configs[index - 1]
            repo = config.get('repo', 'unknown')
            
            # 获取历史记录
            history_key = f"github_webhook:history:{target_id}"
            all_history = self.storage.get(history_key, {})
            repo_history = all_history.get(repo, [])
            
            if not repo_history:
                await event.reply(f"{repo} 暂无历史记录")
                return
            
            # 显示最近10条记录
            recent_history = repo_history[-10:]
            recent_history.reverse()  # 最新的在前
            
            msg = f"{repo} 的最近 {len(recent_history)} 条历史记录：\n\n"
            
            for record in recent_history:
                event_type = record.get('event_type', 'unknown')
                timestamp = record.get('timestamp', 0)
                time_str = format_timestamp(timestamp)
                msg += f"{time_str} | {event_type}\n"
            
            await event.reply(msg)
            
        except Exception as e:
            self.logger.error(f"历史命令失败: {e}", exc_info=True)
            await event.reply("获取历史失败，请稍后重试")
    
    # ========== 路由管理 ==========
    
    async def _restore_routes(self):
        """从存储恢复所有路由"""
        configs = self.storage.get("github_webhook:configs", [])
        
        for config in configs:
            if config.get('enabled'):
                await self._register_route(config)
        
        self.logger.info(f"已恢复 {len(self.webhook_routes)} 个路由")
    
    async def _register_route(self, config):
        """注册单个路由"""
        webhook_path = f"/github-webhook/{config['target_id']}_{config['uuid']}"
        
        # 创建处理器
        async def webhook_handler(request: Request) -> Dict[str, Any]:
            return await self._webhook_request_handler(request, config)
        
        # 注册路由
        self.sdk.router.register_http_route(
            module_name="GitHubWebhook",
            path=webhook_path,
            handler=webhook_handler,
            methods=["POST"]
        )
        
        self.webhook_routes[webhook_path] = config
        self.logger.info(f"注册路由: {webhook_path}")
    
    async def _webhook_request_handler(self, request, config):
        """处理 Webhook 请求"""
        try:
            # 获取请求体
            body = await request.body()
            
            # 获取事件类型
            event_type = request.headers.get('X-GitHub-Event', '')
            
            # 验证签名
            if config.get('webhook_secret'):
                signature = request.headers.get('X-Hub-Signature-256', '')
                if not verify_signature(body, signature, config['webhook_secret']):
                    self.logger.warning(f"签名验证失败: {config['repo']}")
                    return {'status': 'error', 'message': 'Invalid signature'}
            
            # 解析 JSON
            event_data = json.loads(body.decode('utf-8'))
            
            # 处理事件
            await self._process_webhook_event(config, event_type, event_data)
            
            return {'status': 'ok'}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            return {'status': 'error', 'message': 'Invalid JSON'}
        except Exception as e:
            self.logger.error(f"处理 Webhook 请求失败: {e}", exc_info=True)
            await self._send_error_notification(config, str(e))
            return {'status': 'error', 'message': 'Internal error'}
    
    async def _process_webhook_event(self, config, event_type, event_data):
        """处理 Webhook 事件"""
        try:
            # 检查事件类型是否在监听列表中
            events = config.get('events', [])
            if event_type not in events:
                return
            
            # 检查是否去重
            repo = config.get('repo', 'unknown')
            event_key = get_event_key(repo, event_type, event_data)
            
            if event_key:
                dedup_key = f"github_webhook:dedup:{event_key}"
                if self.storage.get(dedup_key):
                    self.logger.debug(f"事件已处理（去重）: {event_key}")
                    return
                
                # 标记已处理
                self.storage.set(dedup_key, True)
            
            # 保存历史
            await self._save_history(config, event_type, event_data)
            
            # 格式化消息
            handler = self.event_handlers.get(event_type)
            if not handler:
                self.logger.warning(f"未知事件类型: {event_type}")
                return
            
            message = handler.format_message(event_data)
            
            # 直接发送消息
            platform = config.get('platform')
            target_id = config.get('target_id')
            target_type = config.get('target_type')
            
            adapter = self.sdk.adapter.get(platform)
            if adapter:
                await adapter.Send.To(target_type, target_id).Text(message)
            else:
                self.logger.error(f"未找到适配器: {platform}")
            
            self.logger.info(f"发送 {event_type} 事件通知: {repo}")
            
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}", exc_info=True)
            raise
    
    async def _send_error_notification(self, config, error):
        """发送错误通知"""
        try:
            # 检查限流
            ratelimit_key = f"github_webhook:error_ratelimit:{config['target_id']}_{config['uuid']}"
            last_error_time = self.storage.get(ratelimit_key, 0)
            
            current_time = int(time.time())
            if current_time - last_error_time < self.config['error_ratelimit']:
                return  # 在限流时间内，不发送
            
            # 更新限流时间
            self.storage.set(ratelimit_key, current_time)
            
            # 构建错误消息
            error_message = f"警告：GitHub Webhook 处理失败\n\n"
            error_message += f"仓库: {config.get('repo', 'unknown')}\n"
            error_message += f"错误: {error}\n\n"
            error_message += "请检查配置或联系管理员"
            
            # 直接发送错误通知
            platform = config.get('platform')
            target_id = config.get('target_id')
            target_type = config.get('target_type')
            
            adapter = self.sdk.adapter.get(platform)
            if adapter:
                await adapter.Send.To(target_type, target_id).Text(error_message)
            else:
                self.logger.error(f"未找到适配器: {platform}")
            
        except Exception as e:
            self.logger.error(f"发送错误通知失败: {e}")
    
    async def _save_history(self, config, event_type, event_data):
        """保存历史记录"""
        try:
            history_key = f"github_webhook:history:{config['target_id']}"
            all_history = self.storage.get(history_key, {})
            repo = config.get('repo', 'unknown')
            repo_history = all_history.get(repo, [])
            
            # 添加新记录
            record = {
                'event_type': event_type,
                'timestamp': int(time.time()),
                'data': event_data,
            }
            repo_history.append(record)
            
            # 限制记录数量
            max_records = self.config.get('max_history_records', 100)
            if len(repo_history) > max_records:
                repo_history = repo_history[-max_records:]
            
            # 保存
            all_history[repo] = repo_history
            self.storage.set(history_key, all_history)
            
        except Exception as e:
            self.logger.error(f"保存历史失败: {e}")
    
    async def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            current_time = int(time.time())
            dedup_ttl = self.config.get('dedup_ttl', 3600)
            
            # 清理去重集合中的过期数据
            dedup_key = f"github_webhook:dedup"
            dedup_set = self.storage.get(dedup_key, [])
            dedup_set = {item for item in dedup_set if current_time - item['timestamp'] <= dedup_ttl}
            self.storage.set(dedup_key, dedup_set)
            
            self.logger.info("过期数据清理完成")
            
        except Exception as e:
            self.logger.error(f"清理过期数据失败: {e}")