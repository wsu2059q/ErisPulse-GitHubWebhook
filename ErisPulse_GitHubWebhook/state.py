"""对象级状态快照：release 附件 diff、PR 提交增量、渲染内容去重，含 TTL 清理。"""

import hashlib
import time

DEFAULT_STATE_TTL = 7 * 86400


def _md5(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


def object_key(event_type: str, event_data: dict) -> str:
    """事件所属业务对象的键（同一对象的事件共享状态）。"""
    if event_type == "push":
        return f"push:{event_data.get('after', '')}"
    if event_type == "issues":
        return f"issue:{(event_data.get('issue', {}) or {}).get('number', 0)}"
    if event_type == "pull_request":
        return f"pr:{(event_data.get('pull_request', {}) or {}).get('number', 0)}"
    if event_type == "release":
        release = event_data.get("release", {}) or {}
        return f"release:{release.get('id', release.get('tag_name', ''))}"
    if event_type == "issue_comment":
        return f"comment:{(event_data.get('comment', {}) or {}).get('id', 0)}"
    if event_type == "pull_request_review":
        return f"review:{(event_data.get('review', {}) or {}).get('id', 0)}"
    if event_type == "workflow_run":
        return f"run:{(event_data.get('workflow_run', {}) or {}).get('id', 0)}"
    if event_type == "star":
        return f"star:{(event_data.get('sender', {}) or {}).get('login', '')}"
    if event_type == "fork":
        return f"fork:{(event_data.get('forkee', {}) or {}).get('id', '')}"
    return f"{event_type}:{int(time.time())}"


def release_snapshot(event_data: dict) -> dict:
    release = event_data.get("release", {}) or {}
    return {
        "tag": release.get("tag_name", ""),
        "title": release.get("name", ""),
        "body_hash": _md5(release.get("body") or ""),
        "assets": {a.get("name", ""): a.get("size", 0)
                   for a in (release.get("assets", []) or []) if a.get("name")},
    }


def diff_release(prev: dict, event_data: dict) -> dict:
    """对比上次快照，返回附件/日志变化；prev 不存在时返回空 diff。"""
    if not prev:
        return {"added": [], "removed": [], "body_changed": False, "title_changed": False}
    cur = release_snapshot(event_data)
    prev_assets = prev.get("assets", {}) or {}
    cur_assets = cur["assets"]
    added = sorted(n for n in cur_assets if n not in prev_assets)
    removed = sorted(n for n in prev_assets if n not in cur_assets)
    return {
        "added": [{"name": n, "size": cur_assets[n]} for n in added],
        "removed": removed,
        "body_changed": cur["body_hash"] != prev.get("body_hash"),
        "title_changed": cur["title"] != prev.get("title"),
    }


def pr_delta(prev: dict, event_data: dict) -> dict:
    """根据上次快照计算 PR synchronize 的提交增量。"""
    pr = event_data.get("pull_request", {}) or {}
    total = pr.get("commits", 0)
    head = (pr.get("head", {}) or {}).get("sha", "")
    if not prev:
        return {"new_commits": None, "total": total, "head": head}
    prev_total = prev.get("commits", 0)
    new_commits = max(0, total - prev_total) if total >= prev_total else None
    return {"new_commits": new_commits, "total": total, "head": head}


class ObjectState:
    """单个监听（target_id + repo）的对象状态，持久化到 sdk.storage。"""

    def __init__(self, storage, target_id, repo, ttl=DEFAULT_STATE_TTL):
        self._storage = storage
        self._key = f"github_webhook:state:{target_id}:{repo}"
        self._ttl = ttl
        self._data = None

    def _load(self) -> dict:
        if self._data is None:
            self._data = self._storage.get(self._key, {}) or {}
        return self._data

    def _save(self):
        self._storage.set(self._key, self._data or {})

    def get(self, obj_key: str, default=None):
        return self._load().get(obj_key, default)

    def set(self, obj_key: str, value: dict):
        data = self._load()
        value["ts"] = time.time()
        data[obj_key] = value
        self._save()

    def doc_seen(self, obj_key: str, doc_hash: str) -> bool:
        """该对象的渲染内容与上次相同则返回 True（视为重复，应跳过发送）。"""
        entry = self._load().get(f"doc:{obj_key}") or {}
        return entry.get("hash") == doc_hash

    def doc_mark(self, obj_key: str, doc_hash: str):
        data = self._load()
        data[f"doc:{obj_key}"] = {"hash": doc_hash, "ts": time.time()}
        self._save()

    def prune(self) -> int:
        """清理超过 TTL 的条目，返回删除数量。"""
        data = self._load()
        if not data:
            return 0
        deadline = time.time() - self._ttl
        kept = {k: v for k, v in data.items()
                if isinstance(v, dict) and v.get("ts", 0) >= deadline}
        removed = len(data) - len(kept)
        if removed:
            self._data = kept
            self._save()
        return removed
