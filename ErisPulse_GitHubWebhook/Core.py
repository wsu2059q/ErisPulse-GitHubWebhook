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
    is_bot_user,
)
from .i18n import t, set_locale
from .policy import decide
from .state import (
    ObjectState,
    object_key,
    release_snapshot,
    diff_release,
    pr_delta,
)
from .templates import GitHubTemplates
from .Renderer import CardRenderer


EVENT_HANDLERS = {
    "push": GitHubTemplates.build_push,
    "issues": GitHubTemplates.build_issues,
    "pull_request": GitHubTemplates.build_pr,
    "release": GitHubTemplates.build_release,
    "star": GitHubTemplates.build_star,
    "fork": GitHubTemplates.build_fork,
    "workflow_run": GitHubTemplates.build_workflow,
    "issue_comment": GitHubTemplates.build_comment,
    "pull_request_review": GitHubTemplates.build_review,
}

# 评论类事件：默认忽略机器人（可按监听用 ghw_set 放行）
COMMENT_EVENTS = {"issue_comment", "pull_request_review"}


def format_message(event_type: str, event_data: dict) -> dict:
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        raise ValueError(t("err.unknown_event_type", event_type=event_type))
    return handler(event_data)


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubWebhook")
        self.storage = sdk.storage
        self.config = self._load_config()
        set_locale(self.config.get("locale", "zh-CN"))
        self.renderer = CardRenderer(sdk, self.logger)
        self.webhook_routes = {}
        self._event_queue = {}
        self._queue_lock = asyncio.Lock()
        self._object_states = {}

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy

        return ModuleLoadStrategy(lazy_load=False, priority=100)

    async def on_load(self, event):
        self.logger.info("模块加载中...")

        if not self.config.get("base_url"):
            self.logger.error(
                "缺少必要配置: base_url，请在 config.toml 中配置 [GitHubWebhook]"
            )
            return

        self._register_commands()
        await self._restore_routes()
        await self._cleanup_expired_data()

        self.logger.info("模块加载完成")

    async def on_unload(self, event):
        self.logger.info("模块卸载中...")
        await self._cleanup_queue()
        self.logger.info("模块卸载完成")

    def _load_config(self):
        config = self.sdk.config.getConfig("GitHubWebhook", {})
        defaults = {
            "base_url": "",
            "locale": "zh-CN",
            "history_ttl": 7,
            "state_ttl": 7 * 86400,
            "merge_window": 5,
            "error_ratelimit": 300,
            "max_history_records": 100,
            "render_card": True,
        }

        for key, value in defaults.items():
            if key not in config or config[key] is None:
                config[key] = value

        return config

    def _get_target_info(self, event):
        if event.is_group_message():
            return event.get_group_id(), "group"
        return event.get_user_id(), "user"

    def _register_commands(self):
        @command("ghw_add", help=t("cmd.help_add"))
        async def add_command(event):
            await self._handle_add_command(event)

        @command("ghw_list", help=t("cmd.help_list"))
        async def list_command(event):
            await self._handle_list_command(event)

        @command("ghw_remove", help=t("cmd.help_remove"))
        async def remove_command(event):
            await self._handle_remove_command(event)

        @command("ghw_set", help=t("cmd.help_set"))
        async def set_command(event):
            await self._handle_set_command(event)

        @command("ghw_history", help=t("cmd.help_history"))
        async def history_command(event):
            await self._handle_history_command(event)

    async def _handle_add_command(self, event):
        try:
            target_id, target_type = self._get_target_info(event)
            platform = event.get_platform()

            await event.reply(t("cmd.input_repo"))
            repo_reply = await event.wait_reply(timeout=60)
            if not repo_reply:
                await event.reply(t("cmd.timeout"))
                return

            repo = repo_reply.get_text().strip()
            if not repo or "/" not in repo:
                await event.reply(t("cmd.bad_repo"))
                return

            await event.reply(t("cmd.input_events"))
            events_reply = await event.wait_reply(timeout=60)
            if not events_reply:
                await event.reply(t("cmd.timeout"))
                return

            events_str = events_reply.get_text().strip()
            events = [e.strip().lower() for e in events_str.split(",") if e.strip()]

            valid_events = [
                "push",
                "issues",
                "pr",
                "release",
                "star",
                "fork",
                "workflow",
                "comment",
                "review",
            ]
            invalid_events = [e for e in events if e not in valid_events]

            if invalid_events:
                await event.reply(t("cmd.invalid_events", events=", ".join(invalid_events)))
                return

            events = [
                "pull_request"
                if e == "pr"
                else "workflow_run"
                if e == "workflow"
                else "issue_comment"
                if e == "comment"
                else "pull_request_review"
                if e == "review"
                else e
                for e in events
            ]

            await event.reply(t("cmd.input_secret"))
            secret_reply = await event.wait_reply(timeout=60)
            if not secret_reply:
                await event.reply(t("cmd.timeout"))
                return

            webhook_secret = secret_reply.get_text().strip()
            if webhook_secret.lower() == "skip" or webhook_secret == "":
                webhook_secret = None

            uuid_short = generate_uuid_short(4)
            webhook_path = f"/{target_id}_{uuid_short}"

            for _ in range(3):
                configs = self.storage.get("github_webhook:configs", [])
                uuid_exists = any(c.get("uuid") == uuid_short for c in configs)

                if uuid_exists:
                    uuid_short = generate_uuid_short(4)
                    webhook_path = f"/{target_id}_{uuid_short}"
                else:
                    break

            config_data = {
                "uuid": uuid_short,
                "target_id": target_id,
                "target_type": target_type,
                "platform": platform,
                "repo": repo,
                "events": events,
                "webhook_secret": webhook_secret,
                "enabled": True,
                "created_at": int(time.time()),
            }

            configs = self.storage.get("github_webhook:configs", [])
            configs.append(config_data)
            self.storage.set("github_webhook:configs", configs)

            await self._register_route(config_data)

            base_url = self.config["base_url"].rstrip("/")
            full_webhook_path = f"/GitHubWebhook{webhook_path}"
            webhook_url = f"{base_url}{full_webhook_path}"

            msg = t(
                "cmd.add_success",
                url=webhook_url,
                secret=t("cmd.secret_set") if webhook_secret else t("cmd.secret_none"),
                events=", ".join(events),
            )

            await event.reply(msg)
            self.logger.info(t("cmd.added_log", repo=repo, target=target_id))

        except Exception as e:
            self.logger.error(f"添加 Webhook 配置失败: {e}", exc_info=True)
            await event.reply(t("cmd.add_failed"))

    async def _handle_list_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get("target_id") == target_id]

            if not target_configs:
                await event.reply(t("cmd.no_configs"))
                return

            msg = t("cmd.config_count", count=len(target_configs))

            for i, config in enumerate(target_configs, 1):
                webhook_path = f"/GitHubWebhook/{config['target_id']}_{config['uuid']}"
                msg += t(
                    "cmd.config_item",
                    i=i,
                    repo=config.get("repo", "unknown"),
                    events=", ".join(config.get("events", [])),
                    status=t("cmd.enabled") if config.get("enabled") else t("cmd.disabled"),
                    path=webhook_path,
                )

            await event.reply(msg)

        except Exception as e:
            self.logger.error(f"列表命令失败: {e}", exc_info=True)
            await event.reply(t("cmd.list_failed"))

    async def _handle_remove_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get("target_id") == target_id]

            if not target_configs:
                await event.reply(t("cmd.no_configs"))
                return

            msg = t("cmd.config_count", count=len(target_configs))
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"

            msg += "\n" + t("cmd.pick_repo_remove")
            await event.reply(msg)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                await event.reply(t("cmd.timeout"))
                return

            try:
                index = int(reply.get_text().strip())
                if index == 0:
                    await event.reply(t("cmd.cancelled"))
                    return

                if index < 1 or index > len(target_configs):
                    await event.reply(t("cmd.invalid_index"))
                    return
            except ValueError:
                await event.reply(t("cmd.invalid_input"))
                return

            config_to_remove = target_configs[index - 1]
            repo = config_to_remove.get("repo", "unknown")

            await event.reply(t("cmd.confirm_delete", repo=repo))

            confirm_reply = await event.wait_reply(timeout=30)
            if not confirm_reply:
                await event.reply(t("cmd.timeout"))
                return

            confirm = confirm_reply.get_text().strip().lower()
            if confirm != "y" and confirm != "yes":
                await event.reply(t("cmd.cancelled"))
                return

            configs = [c for c in configs if c != config_to_remove]
            self.storage.set("github_webhook:configs", configs)

            webhook_path = f"/GitHubWebhook/{config_to_remove['target_id']}_{config_to_remove['uuid']}"
            if webhook_path in self.webhook_routes:
                del self.webhook_routes[webhook_path]

            await event.reply(t("cmd.delete_success"))
            self.logger.info(t("cmd.deleted_log", repo=repo))

        except Exception as e:
            self.logger.error(f"删除命令失败: {e}", exc_info=True)
            await event.reply(t("cmd.delete_failed"))

    EVENT_ALIASES = {
        "pr": "pull_request",
        "pull_request": "pull_request",
        "workflow": "workflow_run",
        "workflow_run": "workflow_run",
        "comment": "issue_comment",
        "issue_comment": "issue_comment",
        "review": "pull_request_review",
        "pull_request_review": "pull_request_review",
        "issues": "issues",
        "release": "release",
        "push": "push",
        "star": "star",
        "fork": "fork",
    }

    def _get_object_state(self, config) -> ObjectState:
        key = (config.get("target_id"), config.get("repo"))
        state = self._object_states.get(key)
        if state is None:
            state = ObjectState(
                self.storage,
                config.get("target_id"),
                config.get("repo"),
                ttl=self.config.get("state_ttl", 7 * 86400),
            )
            self._object_states[key] = state
        return state

    def _build_context(self, state, event_type, event_data):
        """为策略决策准备差量上下文（release 快照 diff、PR 提交增量）。"""
        context = {}
        try:
            action = event_data.get("action", "")
            if event_type == "release" and action == "edited":
                prev = state.get(object_key(event_type, event_data))
                context["release_edited"] = {
                    "prev_exists": prev is not None,
                    "diff": diff_release(prev, event_data) if prev else None,
                }
            elif event_type == "pull_request" and action == "synchronize":
                context["pr"] = pr_delta(state.get(object_key(event_type, event_data)), event_data)
        except Exception as e:
            self.logger.warning(f"构建事件上下文失败: {e}")
        return context

    def _update_state(self, state, event_type, event_data):
        """发送成功后更新对象快照。"""
        try:
            if event_type == "release":
                state.set(object_key(event_type, event_data), release_snapshot(event_data))
            elif event_type == "pull_request":
                pr = event_data.get("pull_request", {}) or {}
                state.set(object_key(event_type, event_data), {
                    "commits": pr.get("commits", 0),
                    "head": (pr.get("head", {}) or {}).get("sha", ""),
                    "title": pr.get("title", ""),
                })
        except Exception as e:
            self.logger.warning(f"更新对象状态失败: {e}")

    def _is_ignored_bot(self, config, event_data) -> bool:
        """评论类事件的机器人过滤：默认忽略，bot_allow 名单放行。"""
        if not is_bot_user(event_data):
            return False
        allow = config.get("bot_allow") or []
        login = (event_data.get("sender", {}) or {}).get("login", "")
        return login not in allow

    def _render_allowed(self, config, platform):
        if config.get("render") is False:
            return False
        if not self.config.get("render_card", True):
            return False
        try:
            supported_methods = sdk.adapter.list_sends(platform)
            if "Image" not in supported_methods:
                return False
        except Exception:
            adapter = getattr(sdk.adapter, platform, None)
            if adapter is None or not hasattr(adapter.Send, "Image"):
                return False
        return self.renderer.available() is True

    async def _try_send_rendered(self, adapter, config, platform, event_type, event_data,
                                 target_type, target_id, presentation=None, state=None):
        if not self._render_allowed(config, platform):
            return False

        if presentation is None:
            presentation = decide(event_type, event_data)
        if presentation.skip:
            return True

        rendered = self.renderer.render(event_type, event_data, presentation.variant, presentation.delta)
        if not rendered:
            return False

        png, link_text, _fallback_text, doc_hash = rendered

        obj_key = object_key(event_type, event_data)
        if state is not None and state.doc_seen(obj_key, doc_hash):
            self.logger.info(f"内容与上次一致，跳过发送: {event_type} {obj_key}")
            return True

        try:
            await adapter.Send.To(target_type, target_id).Image(png, stream=True)
        except Exception as e:
            self.logger.warning(f"渲染卡片发送失败，回退富文本: {e}")
            return False

        if state is not None:
            state.doc_mark(obj_key, doc_hash)

        if presentation.announce and link_text:
            try:
                await adapter.Send.To(target_type, target_id).Text(link_text)
            except Exception as e:
                self.logger.warning(f"链接文本发送失败: {e}")
        return True

    async def _handle_set_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get("target_id") == target_id]

            if not target_configs:
                await event.reply(t("cmd.no_configs"))
                return

            msg = t("cmd.config_count", count=len(target_configs))
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"

            msg += "\n" + t("cmd.pick_repo_set")
            await event.reply(msg)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                await event.reply(t("cmd.timeout"))
                return

            try:
                index = int(reply.get_text().strip())
                if index == 0:
                    await event.reply(t("cmd.cancelled"))
                    return
                if index < 1 or index > len(target_configs):
                    await event.reply(t("cmd.invalid_index"))
                    return
            except ValueError:
                await event.reply(t("cmd.invalid_input"))
                return

            config = target_configs[index - 1]

            render_word = {True: "cmd.render_state_on", False: "cmd.render_state_off", None: "cmd.render_state_auto"}
            render_state = t(render_word.get(config.get("render"), "cmd.render_state_auto"))
            notify = config.get("notify") or {}
            if notify:
                policy_lines = []
                for event_name, actions in notify.items():
                    policy_lines.append(
                        t("cmd.notify_line", event=event_name, actions="、".join(actions))
                        if actions else t("cmd.notify_muted", event=event_name)
                    )
                policy = t("cmd.notify_header") + "\n".join(policy_lines)
            else:
                policy = t("cmd.notify_all")

            bot_allow = config.get("bot_allow") or []
            bot_policy = (
                t("cmd.bot_allow", logins=", ".join(bot_allow)) if bot_allow else t("cmd.bot_default")
            )

            subscribed = "、".join(config.get("events", []))
            await event.reply(t(
                "cmd.settings_view",
                repo=config.get("repo", "unknown"),
                render=render_state,
                notify=policy,
                bot=bot_policy,
                events=subscribed,
            ))

            change_reply = await event.wait_reply(timeout=90)
            if not change_reply:
                await event.reply(t("cmd.timeout"))
                return

            change = change_reply.get_text().strip()
            if not change or change == "0":
                await event.reply(t("cmd.cancelled"))
                return

            error = self._apply_setting(config, change)
            if error:
                await event.reply(error)
                return

            all_configs = self.storage.get("github_webhook:configs", [])
            all_configs = [
                {
                    **c,
                    "render": config.get("render"),
                    "notify": config.get("notify"),
                    "bot_allow": config.get("bot_allow"),
                }
                if c.get("uuid") == config.get("uuid")
                else c
                for c in all_configs
            ]
            self.storage.set("github_webhook:configs", all_configs)

            render_word = {True: "cmd.render_state_on", False: "cmd.render_state_off", None: "cmd.render_state_auto"}
            await event.reply(t("cmd.set_saved", render=t(render_word.get(config.get("render"), "cmd.render_state_auto"))))
            self.logger.info(f"更新监听设置: {config.get('repo')}")

        except Exception as e:
            self.logger.error(f"设置命令失败: {e}", exc_info=True)
            await event.reply(t("cmd.set_failed"))

    def _apply_setting(self, config, change):
        lowered = change.lower()
        if lowered == "clear":
            config.pop("notify", None)
            return None

        parts = change.split()
        if parts[0].lower() == "render":
            if len(parts) != 2 or parts[1].lower() not in ("on", "off", "auto"):
                return t("cmd.bad_render_arg")
            state = {"on": True, "off": False, "auto": None}[parts[1].lower()]
            if state is None:
                config.pop("render", None)
            else:
                config["render"] = state
            return None

        if parts[0].lower() == "bot":
            if len(parts) == 2 and parts[1].lower() == "clear":
                config.pop("bot_allow", None)
                return None
            if len(parts) >= 3 and parts[1].lower() == "allow":
                logins = [x.strip() for p in parts[2:] for x in p.split(",") if x.strip()]
                if not logins:
                    return t("cmd.bad_bot_format")
                config["bot_allow"] = logins
                return None
            return t("cmd.bad_bot_format")

        event_name = self.EVENT_ALIASES.get(parts[0].lower())
        if event_name is None:
            return t("cmd.unknown_event", name=parts[0])
        if event_name not in config.get("events", []):
            return t("cmd.event_not_subscribed", event=event_name)

        if len(parts) == 1 or parts[1].lower() == "all":
            notify = config.get("notify") or {}
            notify.pop(event_name, None)
            if notify:
                config["notify"] = notify
            else:
                config.pop("notify", None)
            return None

        if len(parts) == 2 and parts[1].lower() == "mute":
            notify = config.get("notify") or {}
            notify[event_name] = []
            config["notify"] = notify
            return None

        actions = [a.strip().lower() for a in parts[1].split(",") if a.strip()]
        if len(parts) > 2 or not actions:
            return t("cmd.bad_action_format")

        notify = config.get("notify") or {}
        notify[event_name] = actions
        config["notify"] = notify
        return None

    async def _handle_history_command(self, event):
        try:
            target_id, _ = self._get_target_info(event)
            configs = self.storage.get("github_webhook:configs", [])
            target_configs = [c for c in configs if c.get("target_id") == target_id]

            if not target_configs:
                await event.reply(t("cmd.no_configs"))
                return

            msg = t("cmd.config_count", count=len(target_configs))
            for i, config in enumerate(target_configs, 1):
                msg += f"{i}. {config.get('repo', 'unknown')}\n"

            msg += "\n" + t("cmd.pick_repo_history")
            await event.reply(msg)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                await event.reply(t("cmd.timeout"))
                return

            try:
                index = int(reply.get_text().strip())
                if index == 0:
                    await event.reply(t("cmd.cancelled"))
                    return

                if index < 1 or index > len(target_configs):
                    await event.reply(t("cmd.invalid_index"))
                    return
            except ValueError:
                await event.reply(t("cmd.invalid_input"))
                return

            config = target_configs[index - 1]
            repo = config.get("repo", "unknown")

            history_key = f"github_webhook:history:{target_id}"
            all_history = self.storage.get(history_key, {})
            repo_history = all_history.get(repo, [])

            if not repo_history:
                await event.reply(t("cmd.history_none", repo=repo))
                return

            recent_history = repo_history[-10:]
            recent_history.reverse()

            msg = t("cmd.history_view", repo=repo, count=len(recent_history))

            for record in recent_history:
                event_type = record.get("event_type", "unknown")
                timestamp = record.get("timestamp", 0)
                time_str = format_timestamp(timestamp)
                msg += t("cmd.history_line", time=time_str, event=event_type)

            await event.reply(msg)

        except Exception as e:
            self.logger.error(f"历史命令失败: {e}", exc_info=True)
            await event.reply(t("cmd.history_failed"))

    async def _restore_routes(self):
        configs = self.storage.get("github_webhook:configs", [])

        for config in configs:
            if config.get("enabled"):
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
            methods=["POST"],
        )

        self.webhook_routes[webhook_path] = config
        self.logger.info(f"注册路由: {webhook_path}")

    async def _webhook_request_handler(self, request, config):
        try:
            body = await request.body()
            event_type = request.headers.get("X-GitHub-Event", "")

            if config.get("webhook_secret"):
                signature = request.headers.get("X-Hub-Signature-256", "")
                if not verify_signature(body, signature, config["webhook_secret"]):
                    self.logger.warning(f"签名验证失败: {config['repo']}")
                    return {"status": "error", "message": "Invalid signature"}

            event_data = json.loads(body.decode("utf-8"))

            # 验证仓库是否匹配
            event_repo = event_data.get("repository", {}).get("full_name", "")
            config_repo = config.get("repo", "")
            if event_repo and config_repo and event_repo != config_repo:
                self.logger.warning(
                    f"仓库不匹配: 事件来自 {event_repo}, 但配置是 {config_repo}"
                )
                return {"status": "error", "message": "Repository mismatch"}

            await self._process_webhook_event(config, event_type, event_data)

            return {"status": "ok"}

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            return {"status": "error", "message": "Invalid JSON"}
        except Exception as e:
            self.logger.error(f"处理 Webhook 请求失败: {e}", exc_info=True)
            await self._send_error_notification(config, str(e))
            return {"status": "error", "message": "Internal error"}

    async def _process_webhook_event(self, config, event_type, event_data):
        try:
            events = config.get("events", [])
            if event_type not in events:
                return

            notify = config.get("notify") or {}
            allowed = notify.get(event_type)
            if allowed is not None:
                action = event_data.get("action", "")
                conclusion = ""
                if event_type == "workflow_run":
                    conclusion = event_data.get("workflow_run", {}).get("conclusion", "")
                if action not in allowed and conclusion not in allowed:
                    return

            if event_type in COMMENT_EVENTS and self._is_ignored_bot(config, event_data):
                self.logger.info(
                    f"忽略机器人评论: {(event_data.get('sender', {}) or {}).get('login', '')} @ {config.get('repo')}"
                )
                return

            repo = config.get("repo", "unknown")
            target_id = config.get("target_id")

            await self._save_history(config, event_type, event_data)

            await self._queue_event(config, event_type, event_data, repo, target_id)

        except Exception as e:
            self.logger.error(f"处理事件失败: {e}", exc_info=True)
            raise

    async def _send_error_notification(self, config, error):
        try:
            ratelimit_key = (
                f"github_webhook:error_ratelimit:{config['target_id']}_{config['uuid']}"
            )
            last_error_time = self.storage.get(ratelimit_key, 0)

            current_time = int(time.time())
            if current_time - last_error_time < self.config["error_ratelimit"]:
                return

            self.storage.set(ratelimit_key, current_time)

            error_message = (
                t("err.notify_title") + "\n\n"
                + t("err.notify_repo", repo=config.get('repo', 'unknown')) + "\n"
                + t("err.notify_error", error=error) + "\n\n"
                + t("err.notify_hint")
            )

            platform = config.get("platform")
            target_id = config.get("target_id")
            target_type = config.get("target_type")

            adapter = self.sdk.adapter.get(platform)
            if adapter:
                await adapter.Send.To(target_type, target_id).Text(error_message)
            else:
                self.logger.error(t("err.no_adapter", platform=platform))

        except Exception as e:
            self.logger.error(f"发送错误通知失败: {e}")

    async def _save_history(self, config, event_type, event_data):
        try:
            history_key = f"github_webhook:history:{config['target_id']}"
            all_history = self.storage.get(history_key, {})
            repo = config.get("repo", "unknown")
            repo_history = all_history.get(repo, [])

            record = {
                "event_type": event_type,
                "timestamp": int(time.time()),
                "data": event_data,
            }
            repo_history.append(record)

            max_records = self.config.get("max_history_records", 100)
            if len(repo_history) > max_records:
                repo_history = repo_history[-max_records:]

            all_history[repo] = repo_history
            self.storage.set(history_key, all_history)

        except Exception as e:
            self.logger.error(f"保存历史失败: {e}")

    async def _cleanup_expired_data(self):
        try:
            configs = self.storage.get("github_webhook:configs", [])
            state_ttl = self.config.get("state_ttl", 7 * 86400)
            history_ttl_days = self.config.get("history_ttl", 7)
            now = time.time()

            cleaned_entries = 0
            cleaned_histories = 0

            for config in configs:
                try:
                    if state_ttl and state_ttl > 0:
                        state = ObjectState(
                            self.storage,
                            config.get("target_id"),
                            config.get("repo"),
                            ttl=state_ttl,
                        )
                        cleaned_entries += state.prune()

                    if not (history_ttl_days and history_ttl_days > 0):
                        continue

                    history_key = f"github_webhook:history:{config.get('target_id')}"
                    all_history = self.storage.get(history_key, {})
                    if not all_history:
                        continue

                    changed = False
                    for repo in list(all_history.keys()):
                        records = all_history.get(repo, [])
                        kept = [
                            r for r in records
                            if now - r.get("timestamp", 0) < history_ttl_days * 86400
                        ]
                        if len(kept) != len(records):
                            changed = True
                        if kept:
                            all_history[repo] = kept
                        else:
                            del all_history[repo]
                    if changed:
                        self.storage.set(history_key, all_history)
                        cleaned_histories += 1
                except Exception as e:
                    self.logger.warning(f"清理 {config.get('repo')} 数据失败: {e}")

            self.logger.info(
                f"过期数据清理完成: 状态条目 {cleaned_entries} 条, 历史仓库 {cleaned_histories} 组"
            )
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

    async def _send_with_format(
        self, adapter, target_type: str, target_id: str, format_content: tuple
    ) -> None:
        format_name, content = format_content

        if format_name == "Html":
            await adapter.Send.To(target_type, target_id).Html(content)
        elif format_name == "Markdown":
            await adapter.Send.To(target_type, target_id).Markdown(content)
        else:
            await adapter.Send.To(target_type, target_id).Text(content)

    async def _queue_event(self, config, event_type, event_data, repo, target_id):
        queue_key = f"{target_id}:{repo}:{event_type}"

        async with self._queue_lock:
            if queue_key in self._event_queue:
                queue_item = self._event_queue[queue_key]

                old_task = queue_item.get("task")
                if old_task and not old_task.done():
                    old_task.cancel()

                if event_type == "release":
                    queue_item["events"] = [event_data]
                    queue_item["updated_at"] = time.time()
                else:
                    queue_item["events"].append(event_data)
                    queue_item["updated_at"] = time.time()

                queue_item["task"] = asyncio.create_task(
                    self._process_event_queue(queue_key)
                )
            else:
                queue_item = {
                    "config": config,
                    "event_type": event_type,
                    "events": [event_data],
                    "repo": repo,
                    "target_id": target_id,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "task": asyncio.create_task(self._process_event_queue(queue_key)),
                }
                self._event_queue[queue_key] = queue_item

    async def _process_event_queue(self, queue_key):
        try:
            await asyncio.sleep(self.config.get("merge_window", 5))

            async with self._queue_lock:
                if queue_key not in self._event_queue:
                    return

                queue_item = self._event_queue.pop(queue_key)

            config = queue_item["config"]
            event_type = queue_item["event_type"]
            events = queue_item["events"]
            repo = queue_item["repo"]

            if event_type == "release":
                event_data = events[-1]
                await self._send_single_event(config, event_type, event_data, repo)
            elif event_type == "push":
                combined_event = self._combine_push_events(events)
                if combined_event:
                    await self._send_single_event(
                        config, event_type, combined_event, repo
                    )
            else:
                for event_data in events:
                    await self._send_single_event(config, event_type, event_data, repo)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"处理队列事件失败 ({queue_key}): {e}", exc_info=True)

    async def _send_single_event(self, config, event_type, event_data, repo):
        try:
            platform = config.get("platform")
            target_id = config.get("target_id")
            target_type = config.get("target_type")

            adapter = self.sdk.adapter.get(platform)
            if not adapter:
                self.logger.error(t("err.no_adapter", platform=platform))
                return

            state = self._get_object_state(config)
            context = self._build_context(state, event_type, event_data)
            presentation = decide(event_type, event_data, context)

            if presentation.skip:
                self.logger.info(f"按策略跳过 {event_type}.{event_data.get('action', '')}: {repo}")
                return

            if await self._try_send_rendered(
                adapter, config, platform, event_type, event_data, target_type, target_id,
                presentation=presentation, state=state,
            ):
                self._update_state(state, event_type, event_data)
                self.logger.info(f"发送 {event_type} 事件渲染卡片: {repo}")
                return

            # 渲染不可用：独立事件回退富文本，更新类事件只发一行短文本
            if presentation.announce:
                message_templates = format_message(event_type, event_data)
                format_name, content = self._select_best_format(platform, message_templates)
                await self._send_with_format(
                    adapter, target_type, target_id, (format_name, content)
                )
            else:
                built = self.renderer.build(event_type, event_data, presentation.variant, presentation.delta)
                short_text = built[2] if built else ""
                if short_text:
                    await adapter.Send.To(target_type, target_id).Text(short_text)

            self._update_state(state, event_type, event_data)
            self.logger.info(f"发送 {event_type} 事件通知: {repo}")

        except Exception as e:
            self.logger.error(f"发送事件失败: {e}", exc_info=True)

    def _combine_push_events(self, events):
        if not events:
            return None

        if len(events) == 1:
            return events[0]

        base_event = events[0].copy()
        all_commits = []
        seen_commit_ids = set()

        for event in events:
            commits = event.get("commits", [])
            for commit in commits:
                commit_id = commit.get("id", "")
                if commit_id and commit_id not in seen_commit_ids:
                    seen_commit_ids.add(commit_id)
                    all_commits.append(commit)

        base_event["commits"] = all_commits
        base_event["compare"] = events[-1].get("compare", "")

        head_commit = events[-1].get("head_commit", {})
        if head_commit:
            base_event["head_commit"] = head_commit

        base_event["after"] = events[-1].get("after", "")

        return base_event

    async def _cleanup_queue(self):
        async with self._queue_lock:
            for queue_key, queue_item in self._event_queue.items():
                if queue_item["task"] and not queue_item["task"].done():
                    queue_item["task"].cancel()
                    try:
                        await queue_item["task"]
                    except asyncio.CancelledError:
                        pass
            self._event_queue.clear()
