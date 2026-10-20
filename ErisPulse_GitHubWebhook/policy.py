"""展示策略矩阵：按 (事件类型, action) 决定卡片形态与是否伴随文本。

独立事件（首次发版、PR 新开等）发「完整卡 + 文本」；
更新类事件（PR 新提交、编辑、release 附件跟进等）只发紧凑增量图，不发文本，
仅在渲染不可用时回退为一行短文本。
"""

from dataclasses import dataclass, field


@dataclass
class Presentation:
    variant: str = "full"      # "full" 完整卡 | "compact" 紧凑增量卡
    delta: dict = field(default_factory=dict)
    announce: bool = True      # 是否随图发送一条文本
    skip: bool = False         # 直接跳过，不发任何消息


# PR：视为「独立事件」、值得发文本的动作
_PR_ANNOUNCE = {"opened", "ready_for_review", "reopened"}

# PR：纯管理性动作，默认不通知（notify 白名单只控制过滤，这里控制展示形态）
_PR_SKIP = {
    "labeled", "unlabeled", "review_requested", "review_request_removed",
    "converted_to_draft", "auto_merge_enabled", "auto_merge_disabled",
    "assigned", "unassigned", "locked", "unlocked", "enqueued", "dequeued",
    "transferred",
}


def decide(event_type: str, event_data: dict, context: dict = None) -> Presentation:
    context = context or {}
    action = event_data.get("action", "")

    if event_type == "push":
        return Presentation("full", announce=True)

    if event_type == "star":
        return Presentation("full", announce=True)

    if event_type == "fork":
        return Presentation("full", announce=True)

    if event_type == "workflow_run":
        conclusion = (event_data.get("workflow_run", {}) or {}).get("conclusion", "")
        return Presentation("full", announce=(conclusion == "failure"))

    if event_type == "pull_request":
        pr = event_data.get("pull_request", {}) or {}
        if action in _PR_ANNOUNCE:
            return Presentation("full", announce=True)
        if action == "synchronize":
            return Presentation("compact", announce=False,
                                delta={"kind": "pr_sync", **(context.get("pr") or {})})
        if action == "edited":
            return Presentation("compact", announce=False,
                                delta={"kind": "pr_edited", "changes": event_data.get("changes", {}) or {}})
        if action == "closed":
            merged = bool(pr.get("merged"))
            return Presentation("compact", announce=merged,
                                delta={"kind": "pr_closed", "merged": merged})
        return Presentation(skip=True)

    if event_type == "release":
        if action in ("published", "prereleased", "released", "deleted"):
            return Presentation("full", announce=True)
        if action == "edited":
            edited_ctx = context.get("release_edited") or {}
            if not edited_ctx.get("prev_exists"):
                # 从未通告过这个 release（如 published 被合并窗口吞掉）→ 按首次发布处理
                return Presentation("full", announce=True)
            diff = edited_ctx.get("diff") or {}
            if not (diff.get("added") or diff.get("removed")
                    or diff.get("body_changed") or diff.get("title_changed")):
                return Presentation(skip=True)
            return Presentation("compact", announce=False,
                                delta={"kind": "release_edited", "diff": diff})
        return Presentation(skip=True)

    if event_type == "issues":
        if action == "opened":
            return Presentation("full", announce=True)
        if action in ("closed", "reopened"):
            return Presentation("compact", announce=True,
                                delta={"kind": "issue_state", "action": action})
        if action == "edited":
            return Presentation("compact", announce=False,
                                delta={"kind": "issue_edited", "changes": event_data.get("changes", {}) or {}})
        return Presentation(skip=True)

    if event_type == "issue_comment":
        if action in ("created", "edited"):
            return Presentation("compact", announce=False,
                                delta={"kind": "comment", "action": action})
        return Presentation(skip=True)

    if event_type == "pull_request_review":
        if action == "submitted":
            return Presentation("compact", announce=False,
                                delta={"kind": "review"})
        return Presentation(skip=True)

    return Presentation(skip=True)
