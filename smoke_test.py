"""冒烟测试：策略矩阵 / 状态差量 / 卡片渲染 / i18n / bot 过滤。

运行： .venv/Scripts/python.exe smoke_test.py
不依赖运行中的 ErisPulse 宿主（对 sdk/fastapi 做 stub），不发送任何消息。
"""

import sys
import types


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


try:
    import ErisPulse  # noqa: F401
except ImportError:
    ep = _stub("ErisPulse")
    ep.sdk = _stub("ErisPulse.sdk")
    core = _stub("ErisPulse.Core")
    core.Bases = _stub("ErisPulse.Core.Bases", BaseModule=type("BaseModule", (), {}))
    core.Event = _stub("ErisPulse.Core.Event", command=lambda *a, **k: (lambda f: f))
    ep.Core = core

try:
    import fastapi  # noqa: F401
except ImportError:
    _stub("fastapi", Request=type("Request", (), {}))

from ErisPulse_GitHubWebhook import i18n, policy
from ErisPulse_GitHubWebhook import state as state_mod
from ErisPulse_GitHubWebhook.utils import is_bot_user
from ErisPulse_GitHubWebhook.Renderer import build_card
from ErisPulse_GitHubWebhook.templates import GitHubTemplates

failures = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def pr_event(action, **kw):
    data = {
        "action": action,
        "repository": {"full_name": "ErisPulse/ErisPulse", "id": 1},
        "sender": {"login": "alice", "type": "User"},
        "number": 459,
        "pull_request": {
            "number": 459,
            "title": kw.get("title", "feat: 2.11 即停释热重复体系"),
            "body": "实现细节见更新日志。",
            "html_url": "https://github.com/ErisPulse/ErisPulse/pull/459",
            "commits": kw.get("commits", 1),
            "head": {"ref": "feat/x", "sha": kw.get("sha", "a" * 40)},
            "base": {"ref": "main"},
            "user": {"login": "alice"},
            "merged": kw.get("merged", False),
        },
    }
    if "changes" in kw:
        data["changes"] = kw["changes"]
    return data


def release_event(action="published", assets=None, body="Changelog here", name="v2.11.0"):
    return {
        "action": action,
        "repository": {"full_name": "ErisPulse/ErisPulse", "id": 1},
        "sender": {"login": "wsu2059", "type": "User"},
        "release": {
            "id": 999,
            "tag_name": "v2.11.0",
            "name": name,
            "body": body,
            "html_url": "https://github.com/ErisPulse/ErisPulse/releases/tag/v2.11.0",
            "published_at": "2026-10-20T12:00:00Z",
            "assets": assets or [],
        },
    }


def comment_event(action="created", login="bob", body="看起来不错", bot=False):
    return {
        "action": action,
        "repository": {"full_name": "ErisPulse/ErisPulse", "id": 1},
        "sender": {"login": f"{login}[bot]" if bot else login, "type": "Bot" if bot else "User"},
        "issue": {"number": 42, "title": "某个 Issue", "html_url": "https://github.com/ErisPulse/ErisPulse/issues/42"},
        "comment": {
            "id": 555,
            "body": body,
            "html_url": "https://github.com/ErisPulse/ErisPulse/issues/42#issuecomment-555",
            "user": {"login": login},
        },
    }


def review_event(state_="approved", body="LGTM"):
    return {
        "action": "submitted",
        "repository": {"full_name": "ErisPulse/ErisPulse", "id": 1},
        "sender": {"login": "bob", "type": "User"},
        "pull_request": {"number": 459, "title": "feat: 2.11", "html_url": "https://github.com/ErisPulse/ErisPulse/pull/459"},
        "review": {
            "id": 777,
            "state": state_,
            "body": body,
            "html_url": "https://github.com/ErisPulse/ErisPulse/pull/459#pullrequestreview-777",
            "user": {"login": "bob"},
        },
    }


# ---------- 策略矩阵 ----------

p = policy.decide("pull_request", pr_event("opened"))
check("pr opened -> full + 文本", p.variant == "full" and p.announce and not p.skip)

p = policy.decide("pull_request", pr_event("ready_for_review"))
check("pr ready_for_review -> full + 文本", p.variant == "full" and p.announce)

p = policy.decide("pull_request", pr_event("synchronize", commits=3),
                  {"pr": {"new_commits": 2, "total": 3, "head": "b" * 40}})
check("pr synchronize -> 紧凑增量图", p.variant == "compact" and not p.announce and p.delta.get("new_commits") == 2)

p = policy.decide("pull_request", pr_event("edited", changes={"body": {"from": "old"}}))
check("pr edited -> 紧凑图（无文本）", p.variant == "compact" and not p.announce and p.delta["kind"] == "pr_edited")

p = policy.decide("pull_request", pr_event("closed", merged=True))
check("pr closed(merged) -> 文本", p.announce is True and p.delta["kind"] == "pr_closed")
p = policy.decide("pull_request", pr_event("closed", merged=False))
check("pr closed(未合并) -> 只发图", p.announce is False)

p = policy.decide("pull_request", pr_event("labeled"))
check("pr labeled -> 跳过", p.skip)

p = policy.decide("release", release_event("published"))
check("release published -> full + 文本", p.variant == "full" and p.announce)

ctx = {"release_edited": {"prev_exists": True,
                          "diff": {"added": [{"name": "app.zip", "size": 123}], "removed": [],
                                   "body_changed": False, "title_changed": False}}}
p = policy.decide("release", release_event("edited", assets=[{"name": "app.zip", "size": 123}]), ctx)
check("release edited(新增附件) -> 差量图", p.variant == "compact" and not p.announce and p.delta["kind"] == "release_edited")

ctx_nochg = {"release_edited": {"prev_exists": True,
                                "diff": {"added": [], "removed": [], "body_changed": False, "title_changed": False}}}
p = policy.decide("release", release_event("edited"), ctx_nochg)
check("release edited(无变化) -> 跳过", p.skip)

ctx_noprev = {"release_edited": {"prev_exists": False, "diff": None}}
p = policy.decide("release", release_event("edited"), ctx_noprev)
check("release edited(无快照) -> 按首次发布", p.variant == "full" and p.announce)

p = policy.decide("workflow_run", {"action": "completed", "repository": {"full_name": "a/b"},
                                   "workflow_run": {"conclusion": "success"}})
check("workflow success -> 只发图", p.announce is False)
p = policy.decide("workflow_run", {"action": "completed", "repository": {"full_name": "a/b"},
                                   "workflow_run": {"conclusion": "failure"}})
check("workflow failure -> 文本", p.announce is True)

p = policy.decide("issue_comment", comment_event())
check("comment created -> 紧凑图（无文本）", p.variant == "compact" and not p.announce)
p = policy.decide("issue_comment", comment_event(action="deleted"))
check("comment deleted -> 跳过", p.skip)
p = policy.decide("pull_request_review", review_event())
check("review submitted -> 紧凑图（无文本）", p.variant == "compact" and not p.announce)
p = policy.decide("pull_request_review", review_event(), {})
p = policy.decide("pull_request_review", {"action": "dismissed"})
check("review dismissed -> 跳过", p.skip)

p = policy.decide("issues", {"action": "opened", "repository": {"full_name": "a/b"},
                             "issue": {"number": 1, "title": "t", "html_url": "u"}})
check("issue opened -> full + 文本", p.variant == "full" and p.announce)
p = policy.decide("issues", {"action": "edited", "repository": {"full_name": "a/b"},
                             "issue": {"number": 1, "title": "t", "html_url": "u"},
                             "changes": {"body": {"from": "x"}}})
check("issue edited -> 紧凑图（无文本）", p.variant == "compact" and not p.announce)

# ---------- 状态：release diff / pr 增量 / 内容去重 / TTL ----------

prev = state_mod.release_snapshot(release_event("published", assets=[]))
diff = state_mod.diff_release(prev, release_event("edited", assets=[{"name": "app.zip", "size": 12345}]))
check("diff_release 识别新增附件", len(diff["added"]) == 1 and diff["added"][0]["name"] == "app.zip"
      and not diff["body_changed"])
diff2 = state_mod.diff_release(prev, release_event("edited", body="Changelog changed!"))
check("diff_release 识别日志修订", diff2["body_changed"] and not diff2["added"])


class FakeStorage:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


st = state_mod.ObjectState(FakeStorage(), "g1", "a/b")
pr1 = pr_event("opened", commits=1, sha="a" * 40)
st.set(state_mod.object_key("pull_request", pr1), {"commits": 1, "head": "a" * 40, "title": "t"})
d = state_mod.pr_delta(st.get(state_mod.object_key("pull_request", pr1)),
                       pr_event("synchronize", commits=3, sha="b" * 40))
check("pr_delta 计算 +2 提交", d["new_commits"] == 2 and d["total"] == 3)
d_unknown = state_mod.pr_delta(None, pr_event("synchronize", commits=3))
check("pr_delta 无快照时只有总数", d_unknown["new_commits"] is None and d_unknown["total"] == 3)

check("doc 去重：首次未见", st.doc_seen("pr:459", "h1") is False)
st.doc_mark("pr:459", "h1")
check("doc 去重：相同内容视为重复", st.doc_seen("pr:459", "h1") is True)
check("doc 去重：内容变化不拦截", st.doc_seen("pr:459", "h2") is False)

st2 = state_mod.ObjectState(FakeStorage(), "g2", "a/b", ttl=-1)
st2.set("release:1", {"tag": "v1"})
check("prune 清理过期状态", st2.prune() >= 1)

# ---------- bot 过滤 ----------

check("bot 识别 [bot] 后缀", is_bot_user(comment_event(bot=True)) is True)
check("bot 识别 Bot 类型", is_bot_user({"sender": {"login": "dependabot", "type": "Bot"}}) is True)
check("普通用户非 bot", is_bot_user(comment_event(bot=False)) is False)

# ---------- 渲染：全事件 build_card ----------

def card_ok(name, event_type, event, variant="full", delta=None, expect=None, compact=False):
    built = build_card(event_type, event, variant, delta)
    if not built:
        check(name, False, "build_card 返回 None")
        return
    doc, link_text, fallback_text = built
    ok = bool(doc and fallback_text is not None)
    if compact:
        ok = ok and 'class="wrap compact"' in doc
    else:
        ok = ok and 'class="wrap"' in doc and "wrap compact" not in doc
    if expect:
        ok = ok and all(e in doc for e in expect)
    check(name, ok, doc[:200] if not ok else "")


card_ok("pr opened 完整卡", "pull_request", pr_event("opened"),
        expect=["Pull Request · 打开", "ErisPulse/ErisPulse"])
card_ok("pr synchronize 紧凑卡", "pull_request", pr_event("synchronize", commits=3),
        variant="compact", delta={"kind": "pr_sync", "new_commits": 2, "total": 3, "head": "b" * 40},
        compact=True, expect=["+2 个新提交"])
card_ok("pr edited 紧凑卡", "pull_request",
        pr_event("edited", changes={"title": {"from": "旧标题"}, "body": {"from": "旧"}}),
        variant="compact", delta={"kind": "pr_edited", "changes": {"title": {"from": "旧标题"}, "body": {"from": "旧"}}},
        compact=True, expect=["标题：旧标题"])
card_ok("pr closed merged 紧凑卡", "pull_request", pr_event("closed", merged=True),
        variant="compact", delta={"kind": "pr_closed", "merged": True},
        compact=True, expect=["已合并"])
card_ok("release 完整卡含附件", "release",
        release_event(assets=[{"name": "app.zip", "size": 15462400, "download_count": 3}]),
        expect=["附件（1）", "app.zip", "14.75 MB"])
card_ok("release 附件差量卡", "release",
        release_event("edited", assets=[{"name": "app.zip", "size": 123}]),
        variant="compact",
        delta={"kind": "release_edited", "diff": {"added": [{"name": "app.zip", "size": 123}],
                                                  "removed": [], "body_changed": False, "title_changed": False}},
        compact=True, expect=["Release · 附件", "新增 1 个附件"])
card_ok("release 日志修订差量卡", "release",
        release_event("edited", body="updated"),
        variant="compact",
        delta={"kind": "release_edited", "diff": {"added": [], "removed": [],
                                                  "body_changed": True, "title_changed": False}},
        compact=True, expect=["Release · 日志修订", "更新日志已修订"])
card_ok("push 完整卡", "push", {
    "ref": "refs/heads/main", "pusher": {"name": "alice"},
    "repository": {"full_name": "ErisPulse/ErisPulse"},
    "sender": {"login": "alice"}, "commits": [{"id": "a" * 40, "message": "feat: x", "author": {"name": "a"}}],
    "after": "a" * 40, "compare": "https://github.com/ErisPulse/ErisPulse/compare/a...b",
}, expect=["main 分支有 1 个新提交"])
card_ok("issues opened 完整卡", "issues",
        {"action": "opened", "repository": {"full_name": "a/b"}, "sender": {"login": "u"},
         "issue": {"number": 1, "title": "标题", "body": "内容", "html_url": "u", "labels": [{"name": "bug"}]}},
        expect=["Issue · 创建"])
card_ok("issue closed 紧凑卡", "issues",
        {"action": "closed", "repository": {"full_name": "a/b"}, "sender": {"login": "u"},
         "issue": {"number": 1, "title": "标题", "html_url": "u"}},
        variant="compact", delta={"kind": "issue_state", "action": "closed"},
        compact=True, expect=["Issue · 关闭"])
card_ok("comment 紧凑卡", "issue_comment", comment_event(),
        variant="compact", delta={"kind": "comment", "action": "created"},
        compact=True, expect=["Comment · 创建", "bob"])
card_ok("review 紧凑卡(approved)", "pull_request_review", review_event(),
        variant="compact", delta={"kind": "review"},
        compact=True, expect=["Review · 通过"])
card_ok("review 紧凑卡(changes_requested)", "pull_request_review",
        review_event(state_="changes_requested", body="请改一下"),
        variant="compact", delta={"kind": "review"},
        compact=True, expect=["Review · 请求修改"])
card_ok("workflow 失败卡（红色 kicker）", "workflow_run", {
    "action": "completed", "repository": {"full_name": "a/b"}, "sender": {"login": "u"},
    "workflow_run": {"conclusion": "failure", "name": "CI", "run_number": 7,
                     "head_branch": "main", "head_sha": "a" * 40,
                     "html_url": "https://github.com/a/b/actions/runs/1",
                     "head_commit": {"message": "fix", "author": {"name": "a"}}},
}, expect=["Workflow · 失败", "k-fail"])
card_ok("star 完整卡", "star", {"repository": {"full_name": "a/b", "stargazers_count": 12},
                                "sender": {"login": "u"}}, expect=["Star"])
card_ok("fork 完整卡", "fork", {"repository": {"full_name": "a/b"}, "sender": {"login": "u"},
                                "forkee": {"full_name": "u/b", "html_url": "https://github.com/u/b"}},
        expect=["Fork"])
check("未知事件返回 None", build_card("unknown_event", {}) is None)

# announce 文本 vs 兜底短文本
built = build_card("pull_request", pr_event("opened"))
check("pr opened 有伴随文本", built[1].startswith("#459") and "\n" in built[1])
built = build_card("pull_request", pr_event("synchronize", commits=3), "compact",
                   {"kind": "pr_sync", "new_commits": 2, "total": 3, "head": "b" * 40})
check("pr synchronize 无伴随文本、有兜底短文本", built[1] == "" and "PR #459" in built[2] and "+2" in built[2])
built = build_card("issue_comment", comment_event(), "compact", {"kind": "comment", "action": "created"})
check("comment 兜底短文本含摘要", "bob" in built[2] and "看起来不错" in built[2])

# ---------- 富文本回退模板 ----------

for name, builder, event in [
    ("build_push", GitHubTemplates.build_push, {"ref": "refs/heads/main", "pusher": {"name": "a"},
                                                "repository": {"full_name": "a/b"}, "commits": [], "compare": ""}),
    ("build_issues", GitHubTemplates.build_issues, {"action": "opened", "repository": {"full_name": "a/b"},
                                                    "issue": {"title": "t", "number": 1, "html_url": "u"}, "sender": {"login": "u"}}),
    ("build_pr", GitHubTemplates.build_pr, pr_event("opened")),
    ("build_release", GitHubTemplates.build_release, release_event()),
    ("build_star", GitHubTemplates.build_star, {"repository": {"full_name": "a/b", "stargazers_count": 1}, "sender": {"login": "u"}}),
    ("build_fork", GitHubTemplates.build_fork, {"repository": {"full_name": "a/b"}, "sender": {"login": "u"},
                                                "forkee": {"full_name": "u/b", "html_url": "x"}}),
    ("build_workflow", GitHubTemplates.build_workflow, {"action": "completed", "repository": {"full_name": "a/b"},
                                                        "workflow_run": {"conclusion": "success", "name": "CI", "run_number": 1,
                                                                         "head_branch": "main", "head_sha": "a" * 40,
                                                                         "html_url": "u", "created_at": "2026-10-20T10:00:00Z",
                                                                         "updated_at": "2026-10-20T10:01:30Z",
                                                                         "head_commit": {"message": "m", "author": {"name": "a"}}}}),
    ("build_comment", GitHubTemplates.build_comment, comment_event()),
    ("build_review", GitHubTemplates.build_review, review_event()),
]:
    result = builder(event)
    check(name, all(isinstance(result.get(k), str) and result.get(k) for k in ("html", "markdown", "text")))

# ---------- i18n ----------

i18n.set_locale("en")
built = build_card("pull_request", pr_event("opened"))
check("en: pr opened kicker", "Pull Request · opened" in built[0])
check("en: announce text", built[1].startswith("#459"))
built = build_card("release", release_event("edited", assets=[{"name": "app.zip", "size": 123}]),
                   "compact", {"kind": "release_edited",
                               "diff": {"added": [{"name": "app.zip", "size": 123}], "removed": [],
                                        "body_changed": False, "title_changed": False}})
check("en: release asset delta card", "1 assets added" in built[0])
check("en: t() 缺失 key 回退", i18n.t("no.such.key") == "no.such.key")
i18n.set_locale("zh-CN")
built = build_card("pull_request", pr_event("opened"))
check("zh-CN: 切回中文", "Pull Request · 打开" in built[0])

print()
if failures:
    print(f"共 {len(failures)} 项失败: {failures}")
    sys.exit(1)
print("全部通过")
