import asyncio
import time
import json
from typing import Dict, Any

from fastapi import Request

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command

from .utils import (
    generate_uuid_short,
    verify_signature,
    format_timestamp,
)
from .templates import GitHubTemplates


EVENT_HANDLERS = {
    'push': GitHubTemplates.build_push,
    'issues': GitHubTemplates.build_issues,
    'pull_request': GitHubTemplates.build_pr,
    'release': GitHubTemplates.build_release,
    'star': GitHubTemplates.build_star,
    'fork': GitHubTemplates.build_fork,
    'workflow_run': GitHubTemplates.build_workflow,
}


def format_message(event_type: str, event_data: dict) -> dict:
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        raise ValueError(f"未知事件类型: {event_type}")
    return handler(event_data)


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubWebhook")
        self.storage = sdk.storage
        self.config = self._load_config()
        self.webhook_routes = {}
    
    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(
            lazy_load=False,
            priority=100
        )
    
    async def on_load(self, event):
        self.logger.info("模块加载中...")
        
        if not self.config.get('base_url'):
            self.logger.error("缺少必要配置: base_url，请在 config.toml 中配置 [GitHubWebhook]")
            return
        
        self._register_commands()
        await self._restore_routes()
        await self._cleanup_expired_data()
        
        self.logger.info("模块加载完成")
    
    async def on_unload(self, event):
        self.logger.info("模块卸载中...")
        self.logger.info("模块卸载完成")
    
    def _load_config(self):
        config = self.sdk.config.getConfig("GitHubWebhook", {})
        defaults = {
            'base_url': '',
            'history_ttl': 7,
            'error_ratelimit': 300,
            'max_history_records': 100,
        }
        
        for key, value in defaults.items():
            if key not in config or not config[key]:
                config[key] = value
        
        return config
    
    def _get_target_info(self, event):
        if event.is_group_message():
            return event.get_group_id(), "group"
        return event.get_user_id(), "user"
    
    def _register_commands(self):
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
    
    async def _handle_add_command(self, event):
        try:
            target_id, target_type = self._get_target_info(event)
            platform = event.get_platform()
            
            await event.reply("请输入仓库名称（格式：username/repo）")
            repo_reply = await event.wait_reply(timeout=60)
            if not repo_reply:
                await event.reply("操作超时")
                return
            
            repo = repo_reply.get_text().strip()
            if not repo or '/' not in repo:
                await event.reply("仓库名称格式错误，应为 username/repo")
                return
            
            await event.reply(f"请选择要监听的事件（push,issues,pr,release,star,fork,workflow - 多个用逗号分隔）")
            events_reply = await event.wait_reply(timeout=60)
            if not events_reply:
                await event.reply("操作超时")
                return
            
            events_str = events_reply.get_text().strip()
            events = [e.strip().lower() for e in events_str.split(',') if e.strip()]
            
            valid_events = ['push', 'issues', 'pr', 'release', 'star', 'fork', 'workflow']
            invalid_events = [e for e in events if e not in valid_events]
            
            if invalid_events:
                await event.reply(f"无效的事件类型: {', '.join(invalid_events)}")
                return
            
            events = [
                'pull_request' if e == 'pr' else
                'workflow_run' if e == 'workflow' else e
                for e in events
            ]
            
            await event.reply("请输入 Webhook Secret（可选，发送空格或 skip 跳过）")
            secret_reply = await event.wait_reply(timeout=60)
            if not secret_reply:
                await event.reply("操作超时")
                return
            
            webhook_secret = secret_reply.get_text().strip()
            if webhook_secret.lower() == 'skip' or webhook_secret == '':
                webhook_secret = None
            
            uuid_short = generate_uuid_short(4)
            webhook_path = f"/{target_id}_{uuid_short}"
            
            for _ in range(3):
                configs = self.storage.get("github_webhook:configs", [])
                uuid_exists = any(c.get('uuid') == uuid_short for c in configs)
                
                if uuid_exists:
                    uuid_short = generate_uuid_short(4)
                    webhook_path = f"/{target_id}_{uuid_short}"
                else:
                    break
            
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
            
            configs = self.storage.get("github_webhook:configs", [])
            configs.append(config_data)
            self.storage.set("github_webhook:configs", configs)
            
            await self._register_route(config_data)
            
            base_url = self.config['base_url'].rstrip('/')
            full_webhook_path = f"/GitHubWebhook{webhook_path}"
            webhook_url = f"{base_url}{full_webhook_path}"
            
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
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            
            for i, config in enumerate(target_configs, 1):
                repo = config.get('repo', 'unknown')
                events = ', '.join(config.get('events', []))
                enabled = '启用' if config.get('enabled') else '禁用'
                webhook_path = f"/GitHubWebhook/{config['target_id']}_{config['uuid']}"
                
                msg += f"{i}. {repo}\n"
                msg += f"   监听事件: {events}\n"
                msg += f"   状态: {enabled}\n"
                msg += f"   Webhook URL: {webhook_path}\n\n"
            
            await event.reply(msg)
            
        except Exception as e:
            self.logger.error(f"列表命令失败: {e}", exc_info=True)
            await event.reply("获取列表失败，请稍后重试")
    
    async def _handle_remove_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"
            
            msg += "\n请输入要删除的序号（输入 0 取消）"
            await event.reply(msg)
            
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
            
            config_to_remove = target_configs[index - 1]
            repo = config_to_remove.get('repo', 'unknown')
            
            await event.reply(f"确认删除 {repo} 的监听配置吗？（y/n）")
            
            confirm_reply = await event.wait_reply(timeout=30)
            if not confirm_reply:
                await event.reply("操作超时")
                return
            
            confirm = confirm_reply.get_text().strip().lower()
            if confirm != 'y' and confirm != 'yes':
                await event.reply("已取消操作")
                return
            
            configs = [c for c in configs if c != config_to_remove]
            self.storage.set("github_webhook:configs", configs)
            
            webhook_path = f"/GitHubWebhook/{config_to_remove['target_id']}_{config_to_remove['uuid']}"
            if webhook_path in self.webhook_routes:
                del self.webhook_routes[webhook_path]
            
            await event.reply("删除成功！")
            self.logger.info(f"删除 Webhook 配置: {repo}")
            
        except Exception as e:
            self.logger.error(f"删除命令失败: {e}", exc_info=True)
            await event.reply("删除失败，请稍后重试")
    
    async def _handle_history_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get('target_id') == target_id]
            
            if not target_configs:
                await event.reply("当前还没有配置任何 Webhook 监听")
                return
            
            msg = f"当前共有 {len(target_configs)} 个监听配置：\n\n"
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"
            
            msg += "\n请选择要查看历史的仓库（输入 0 取消）"
            await event.reply(msg)
            
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
            
            config = target_configs[index - 1]
            repo = config.get('repo', 'unknown')
            
            history_key = f"github_webhook:history:{target_id}"
            all_history = self.storage.get(history_key, {})
            repo_history = all_history.get(repo, [])
            
            if not repo_history:
                await event.reply(f"{repo} 暂无历史记录")
                return
            
            recent_history = repo_history[-10:]
            recent_history.reverse()
            
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
    
    async def _restore_routes(self):
        configs = self.storage.get("github_webhook:configs", [])
        
        for config in configs:
            if config.get('enabled'):
                await self._register_route(config)
        
        self.logger.info(f"已恢复 {len(self.webhook_routes)} 个路由")
    
    async def _register_route(self, config):
        webhook_path = f"/{config['target_id']}_{config['uuid']}"
        
        async def webhook_handler(request: Request) -> Dict[str, Any]:
            return await self._webhook_request_handler(request, config)
        
        self.sdk.router.register_http_route(
            module_name="GitHubWebhook",
            path=webhook_path,
            handler=webhook_handler,
            methods=["POST"]
        )
        
        self.webhook_routes[webhook_path] = config
        self.logger.info(f"注册路由: {webhook_path}")
    
    async def _webhook_request_handler(self, request, config):
        try:
            body = await request.body()
            event_type = request.headers.get('X-GitHub-Event', '')
            
            if config.get('webhook_secret'):
                signature = request.headers.get('X-Hub-Signature-256', '')
                if not verify_signature(body, signature, config['webhook_secret']):
                    self.logger.warning(f"签名验证失败: {config['repo']}")
                    return {'status': 'error', 'message': 'Invalid signature'}
            
            event_data = json.loads(body.decode('utf-8'))
            
            # 验证仓库是否匹配
            event_repo = event_data.get('repository', {}).get('full_name', '')
            config_repo = config.get('repo', '')
            if event_repo and config_repo and event_repo != config_repo:
                self.logger.warning(f"仓库不匹配: 事件来自 {event_repo}, 但配置是 {config_repo}")
                return {'status': 'error', 'message': 'Repository mismatch'}
            
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
        try:
            events = config.get('events', [])
            if event_type not in events:
                return
            
            repo = config.get('repo', 'unknown')
            
            await self._save_history(config, event_type, event_data)
            
            message_templates = format_message(event_type, event_data)
            
            platform = config.get('platform')
            target_id = config.get('target_id')
            target_type = config.get('target_type')
            
            adapter = self.sdk.adapter.get(platform)
            if not adapter:
                self.logger.error(f"未找到适配器: {platform}")
                return
            
            format_name, content = self._select_best_format(platform, message_templates)
            await self._send_with_format(adapter, target_type, target_id, (format_name, content))
            
            self.logger.info(f"发送 {event_type} 事件通知: {repo}")
            
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}", exc_info=True)
            raise
    
    async def _send_error_notification(self, config, error):
        try:
            ratelimit_key = f"github_webhook:error_ratelimit:{config['target_id']}_{config['uuid']}"
            last_error_time = self.storage.get(ratelimit_key, 0)
            
            current_time = int(time.time())
            if current_time - last_error_time < self.config['error_ratelimit']:
                return
            
            self.storage.set(ratelimit_key, current_time)
            
            error_message = f"警告：GitHub Webhook 处理失败\n\n"
            error_message += f"仓库: {config.get('repo', 'unknown')}\n"
            error_message += f"错误: {error}\n\n"
            error_message += "请检查配置或联系管理员"
            
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
        try:
            history_key = f"github_webhook:history:{config['target_id']}"
            all_history = self.storage.get(history_key, {})
            repo = config.get('repo', 'unknown')
            repo_history = all_history.get(repo, [])
            
            record = {
                'event_type': event_type,
                'timestamp': int(time.time()),
                'data': event_data,
            }
            repo_history.append(record)
            
            max_records = self.config.get('max_history_records', 100)
            if len(repo_history) > max_records:
                repo_history = repo_history[-max_records:]
            
            all_history[repo] = repo_history
            self.storage.set(history_key, all_history)
            
        except Exception as e:
            self.logger.error(f"保存历史失败: {e}")
    
    async def _cleanup_expired_data(self):
        try:
            self.logger.info("过期数据清理完成")
        except Exception as e:
            self.logger.error(f"清理过期数据失败: {e}")
    
    def _select_best_format(self, platform: str, templates: Dict[str, str]) -> tuple:
        try:
            supported_methods = sdk.adapter.list_sends(platform)
            
            if "Html" in supported_methods:
                return ("Html", templates["html"])
            elif "Markdown" in supported_methods:
                return ("Markdown", templates["markdown"])
            else:
                return ("Text", templates["text"])
        except Exception as e:
            self.logger.warning(f"list_sends 检测失败: {e}，尝试使用 hasattr 兜底")

            adapter = getattr(sdk.adapter, platform)
            send_obj = adapter.Send
            
            if hasattr(send_obj, "Html"):
                return ("Html", templates["html"])
            elif hasattr(send_obj, "Markdown"):
                return ("Markdown", templates["markdown"])
            else:
                return ("Text", templates["text"])
    
    async def _send_with_format(self, adapter, target_type: str, target_id: str, 
                                format_content: tuple) -> None:
        format_name, content = format_content
        
        if format_name == "Html":
            await adapter.Send.To(target_type, target_id).Html(content)
        elif format_name == "Markdown":
            await adapter.Send.To(target_type, target_id).Markdown(content)
        else:
            await adapter.Send.To(target_type, target_id).Text(content)