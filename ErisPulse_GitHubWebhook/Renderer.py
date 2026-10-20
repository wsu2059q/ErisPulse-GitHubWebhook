import base64
import hashlib
import html
import io
import re

from .i18n import t, option, get_locale

CARD_WIDTH = 880
BODY_BUDGET = 2500
BODY_BUDGET_COMPACT = 700
COMMIT_LIMIT = 6
ASSET_LIMIT = 8
QR_SIZE = 132

ACCENT = "#ff3366"
MUTED = "#6b7280"

CARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Roboto", "Noto Sans SC", sans-serif; }
.wrap { background: #ffffff; padding: 56px 56px 48px; }
.wrap.compact { padding: 36px 44px 32px; }
.compact .title { margin-top: 18px; font-size: 36px; }
.compact .meta { margin-top: 10px; font-size: 21px; }
.compact .rule { margin: 18px 0 6px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.kicker { font-size: 23px; font-weight: 700; letter-spacing: 4px;
  text-transform: uppercase; color: #000000; }
.kicker.k-fail { color: #ff3366; }
.repo { font-family: "Source Code Pro", monospace; font-size: 23px; color: #6b7280; }
.title { margin-top: 28px; font-size: 54px; font-weight: 700; letter-spacing: -1px;
  color: #000000; line-height: 1.25; }
.meta { margin-top: 14px; font-size: 25px; color: #6b7280; }
.rule { height: 2px; background: #000000; margin: 28px 0 8px; }
.body { font-size: 28px; line-height: 1.6; color: #000000; padding-top: 14px; }
.body .p-p { margin: 9px 0; }
.body .p-strong { font-weight: 700; }
.body .p-h { font-size: 30px; font-weight: 700; letter-spacing: -0.5px; margin: 24px 0 10px; }
.body .p-q { font-style: italic; color: #6b7280; margin: 10px 0; padding-left: 20px; }
.body .p-li { margin: 8px 0; padding-left: 36px; text-indent: -36px; }
.body .p-li2 { margin: 7px 0; padding-left: 72px; text-indent: -36px;
  font-size: 27px; color: #000000; }
.body .cb { display: inline-block; width: 24px; height: 24px; border: 3px solid #000000;
  margin-right: 16px; vertical-align: -1px; }
.body .cb-done { background: #000000; }
.body .p-code { font-family: "Source Code Pro", monospace; font-size: 25px; }
.body .p-pre { font-family: "Source Code Pro", monospace; font-size: 23px; line-height: 1.55;
  border: 2px solid #000000; padding: 18px 22px; margin: 16px 0; }
.body .p-hr { height: 1px; background: #000000; margin: 20px 0; }
.body .p-more { margin-top: 12px; font-style: italic; color: #6b7280; }
.body .chip { display: inline-block; margin: 0 10px 10px 0; padding: 3px 16px;
  border: 2px solid #000000; font-size: 23px; font-weight: 700; letter-spacing: 1px; }
.body .c-item { margin: 16px 0; }
.body .c-sha { font-family: "Source Code Pro", monospace; font-size: 24px;
  font-weight: 700; color: #000000; }
.body .c-author { font-size: 24px; color: #6b7280; }
.body .c-msg { margin-top: 4px; font-size: 26px; }
.body .a-item { margin: 10px 0; }
.body .a-name { font-family: "Source Code Pro", monospace; font-size: 24px;
  font-weight: 700; color: #000000; }
.body .a-meta { font-size: 22px; color: #6b7280; }
.d-rows { padding-top: 10px; }
.d-row { font-size: 25px; margin: 10px 0; color: #000000; }
.d-row.d-strong { font-weight: 700; }
.foot { margin-top: 32px; padding-top: 24px; border-top: 2px solid #000000; font-size: 25px;
  display: flex; justify-content: space-between; align-items: center; }
.foot .f-text { font-size: 25px; }
.foot .f-label { font-weight: 700; color: #ff3366; }
.foot .f-url { font-family: "Source Code Pro", monospace; color: #6b7280; word-break: break-all; }
.foot .qr { width: 132px; height: 132px; margin-left: 30px; }
.tags { font-size: 24px; font-weight: 700; letter-spacing: 1px; color: #000000;
  padding-top: 20px; }
.tags .t-muted { color: #6b7280; font-weight: 400; letter-spacing: 0; }
"""


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_COMMENT_OPEN = re.compile(r"<!--.*$", re.DOTALL)
_TASK_ITEM = re.compile(r"^\[([ xX])\]\s+(.*)$")


def _esc(text):
    return html.escape(str(text), quote=False)


def _weight(text):
    return sum(1.0 if ord(ch) > 0x2E7F else 0.55 for ch in text)


def _fit_text(md_text, budget=BODY_BUDGET):
    used = 0.0
    out_lines = []
    truncated = False
    for line in md_text.split("\n"):
        w = _weight(line)
        if used + w > budget:
            remain = budget - used
            if remain > 8:
                count = 0
                acc = 0.0
                for ch in line:
                    acc += 1.0 if ord(ch) > 0x2E7F else 0.55
                    count += 1
                    if acc >= remain:
                        break
                out_lines.append(line[:count] + "……")
            truncated = True
            break
        used += w
        out_lines.append(line)
    return "\n".join(out_lines), truncated


_INLINE_CODE = re.compile(r"`([^`]+)`")
_INLINE_STRONG = re.compile(r"\*\*(.+?)\*\*")
_INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text):
    text = _esc(text)
    text = _INLINE_CODE.sub(lambda m: f'<span class="p-code">{m.group(1)}</span>', text)
    text = _INLINE_STRONG.sub(lambda m: f'<span class="p-strong">{m.group(1)}</span>', text)
    text = _INLINE_LINK.sub(lambda m: m.group(1), text)
    return text


def _body_md(md_text, prefix="", budget=BODY_BUDGET, extra=""):
    md_text = _HTML_COMMENT.sub("", md_text)
    md_text = _HTML_COMMENT_OPEN.sub("", md_text)
    source, truncated = _fit_text(md_text, budget)
    parts = [prefix] if prefix else []
    in_code = False
    code_lines = []
    for line in source.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                parts.append(f'<div class="p-pre">{_esc(chr(10).join(code_lines))}</div>')
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if re.match(r"^-{3,}\s*$", stripped):
            parts.append('<div class="p-hr"></div>')
            continue
        header = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header:
            parts.append(f'<div class="p-h">{_inline(header.group(2))}</div>')
            continue
        if stripped.startswith(">"):
            parts.append(f'<div class="p-q">{_inline(stripped[1:].strip())}</div>')
            continue
        list_match = re.match(r"^(\s*)-\s+(.*)$", line)
        if list_match:
            content = list_match.group(2)
            task = _TASK_ITEM.match(content)
            if task:
                box = '<span class="cb cb-done"></span>' if task.group(1).lower() == "x" else '<span class="cb"></span>'
                cls = "p-li2" if list_match.group(1) else "p-li"
                parts.append(f'<div class="{cls}">{box}{_inline(task.group(2))}</div>')
                continue
            dash = "–&nbsp; "
            if list_match.group(1):
                parts.append(f'<div class="p-li2">{dash}{_inline(list_match.group(2))}</div>')
            else:
                parts.append(f'<div class="p-li">{dash}{_inline(list_match.group(2))}</div>')
            continue
        if not stripped:
            continue
        parts.append(f'<div class="p-p">{_inline(stripped)}</div>')
    if extra:
        parts.append(extra)
    if truncated:
        parts.append(f'<div class="p-more">{_esc(t("card.truncated"))}</div>')
    if not parts:
        return ""
    return f'<div class="body">{"".join(parts)}</div>'


def _chips(labels):
    if not labels:
        return ""
    names = " · ".join(l.get("name", "") for l in labels)
    return f'<div class="tags"><span class="t-muted">{_esc(t("card.labels"))}&nbsp;&nbsp;</span>{_esc(names)}</div>'


def _commits_body(commits):
    if not commits:
        return ""
    rows = []
    for commit in commits[:COMMIT_LIMIT]:
        sha = commit.get("id", "")[:7]
        author = commit.get("author", {}).get("name", "unknown")
        message = commit.get("message", "").split("\n")[0]
        rows.append(
            f'<div class="c-item"><span class="c-sha">{_esc(sha)}</span>'
            f'<span class="c-author"> · {_esc(author)}</span>'
            f'<div class="c-msg">{_esc(message)}</div></div>'
        )
    if len(commits) > COMMIT_LIMIT:
        rows.append(f'<div class="p-more">{_esc(t("card.commits_more", count=len(commits)))}</div>')
    return f'<div class="body">{"".join(rows)}</div>'


def _fmt_size(num):
    try:
        num = int(num or 0)
    except (TypeError, ValueError):
        num = 0
    if num >= 1024 ** 3:
        return f"{num / 1024 ** 3:.2f} GB"
    if num >= 1024 ** 2:
        return f"{num / 1024 ** 2:.2f} MB"
    if num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num} B"


def _assets_rows(assets):
    if not assets:
        return ""
    rows = [f'<div class="p-h">{_esc(t("card.assets", count=len(assets)))}</div>']
    for asset in assets[:ASSET_LIMIT]:
        name = asset.get("name", "")
        meta = f" · {_fmt_size(asset.get('size', 0))}"
        downloads = asset.get("download_count", 0)
        if downloads:
            meta += f" · {_esc(t('card.downloads', count=downloads))}"
        rows.append(
            f'<div class="a-item"><span class="a-name">{_esc(name)}</span>'
            f'<span class="a-meta">{meta}</span></div>'
        )
    if len(assets) > ASSET_LIMIT:
        rows.append(f'<div class="p-more">{_esc(t("card.assets_more", count=len(assets)))}</div>')
    return "".join(rows)


def _delta_rows(delta, event_data):
    """紧凑增量卡的 delta 行。"""
    kind = delta.get("kind")
    rows = []

    def add(text, strong=False):
        cls = "d-row d-strong" if strong else "d-row"
        rows.append(f'<div class="{cls}">{_esc(text)}</div>')

    if kind == "pr_sync":
        new_commits = delta.get("new_commits")
        total = delta.get("total", 0)
        sha = (delta.get("head") or "")[:7]
        if new_commits:
            add(t("delta.new_commits", count=new_commits, total=total), strong=True)
        elif total:
            add(t("delta.commits_total", count=total), strong=True)
        if sha:
            add(t("delta.head_sha", sha=sha))

    elif kind in ("pr_edited", "issue_edited"):
        changes = delta.get("changes", {}) or {}
        pr = event_data.get("pull_request", {}) or {}
        issue = event_data.get("issue", {}) or {}
        current_title = pr.get("title") or issue.get("title") or ""
        title_change = changes.get("title") or {}
        if title_change.get("from") is not None:
            add(t("delta.title_changed", old=title_change.get("from", ""), new=current_title), strong=True)
        if "body" in changes:
            add(t("delta.body_changed"))
        base_change = changes.get("base")
        if isinstance(base_change, dict) and base_change.get("from") is not None:
            old_from = base_change.get("from")
            old_ref = old_from.get("ref", "") if isinstance(old_from, dict) else old_from
            new_ref = (pr.get("base", {}) or {}).get("ref", "")
            add(t("delta.base_changed", old=old_ref, new=new_ref))

    elif kind == "release_edited":
        diff = delta.get("diff", {}) or {}
        added = diff.get("added") or []
        removed = diff.get("removed") or []
        if added:
            add(t("delta.assets_added", count=len(added)), strong=True)
            for asset in added[:ASSET_LIMIT]:
                rows.append(
                    f'<div class="a-item"><span class="a-name">{_esc(asset.get("name", ""))}</span>'
                    f'<span class="a-meta"> · {_fmt_size(asset.get("size", 0))}</span></div>'
                )
        if removed:
            add(t("delta.assets_removed", count=len(removed)))
        if diff.get("body_changed") or diff.get("title_changed"):
            add(t("delta.changelog_updated"))

    return ('<div class="d-rows">' + "".join(rows) + "</div>") if rows else ""


def _date(iso):
    return iso[:10] if isinstance(iso, str) else ""


def _strip_scheme(url):
    return url.replace("https://", "").replace("http://", "") if url else ""


def _qr_data_url(url, cache={}):
    if not url:
        return ""
    if url in cache:
        return cache[url]
    try:
        import segno

        buf = io.BytesIO()
        segno.make(url, error="m").save(buf, kind="png", scale=6, border=1)
        data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""
    if len(cache) > 64:
        cache.clear()
    cache[url] = data_url
    return data_url


def build_card(event_type, event_data, variant="full", delta=None):
    """渲染卡片 HTML。返回 (document, link_text, fallback_text)；未知事件返回 None。

    link_text: 独立事件随图发送的文本；fallback_text: 更新类事件渲染不可用时的短文本。
    """
    delta = delta or {}
    compact = variant == "compact"
    budget = BODY_BUDGET_COMPACT if compact else BODY_BUDGET

    repo = event_data.get("repository", {})
    repo_name = repo.get("full_name", "unknown/repo")
    repo_url = f"https://github.com/{repo_name}"
    sender = event_data.get("sender", {}).get("login", "unknown")

    kicker = ""
    title = ""
    meta = ""
    body_html = ""
    url = repo_url
    link_text = ""
    fallback_text = ""
    foot = t("card.view_details")

    if event_type == "release":
        release = event_data.get("release", {})
        tag = release.get("tag_name", "unknown")
        name = release.get("name", "")
        version = f"{name} ({tag})" if name and name != tag else tag
        body = release.get("body", "") or ""
        assets = release.get("assets", []) or []
        published = _date(release.get("published_at", ""))
        url = release.get("html_url", repo_url)

        if compact and delta.get("kind") == "release_edited":
            diff = delta.get("diff", {}) or {}
            has_asset_change = bool(diff.get("added") or diff.get("removed"))
            kicker = t("kicker.release_assets" if has_asset_change else "kicker.release_changelog")
            title = version
            meta = f"{repo_name} · {t('card.published_by', sender=sender)}"
            body_html = _delta_rows(delta, event_data)
            if diff.get("added"):
                fallback_text = t("fallback.release_assets", version=version,
                                  count=len(diff["added"]), url=url)
            elif diff.get("removed"):
                fallback_text = t("fallback.release_removed", version=version,
                                  count=len(diff["removed"]), url=url)
            else:
                fallback_text = t("fallback.release_changelog", version=version, url=url)
        else:
            kicker = t("kicker.release")
            title = version
            meta = f"{repo_name} · {t('card.published_by', sender=sender)}"
            if published:
                meta += f" · {published}"
            body_html = _body_md(body, budget=budget, extra=_assets_rows(assets)) if (body or assets) else ""
            link_text = t("link.release", version=version, url=url)
            fallback_text = link_text

    elif event_type == "push":
        branch = event_data.get("ref", "").replace("refs/heads/", "")
        pusher = event_data.get("pusher", {}).get("name", "unknown")
        commits = event_data.get("commits", [])
        compare = event_data.get("compare", "")
        kicker = t("kicker.push")
        title = t("card.push_title", branch=branch, count=len(commits))
        meta = f"{repo_name} · {t('card.pusher', sender=pusher)}"
        body_html = _commits_body(commits)
        url = compare or repo_url
        link_text = t("link.push", branch=branch, count=len(commits), url=url)
        fallback_text = link_text
        foot = t("card.view_compare") if compare else t("card.view_repo")

    elif event_type == "issues":
        issue = event_data.get("issue", {})
        action = event_data.get("action", "unknown")
        number = issue.get("number", 0)
        title = issue.get("title", "unknown")
        body = issue.get("body", "") or ""
        labels = issue.get("labels", [])
        url = issue.get("html_url", repo_url)

        if compact:
            if delta.get("kind") == "issue_edited":
                changes = delta.get("changes", {}) or {}
                kicker = t("kicker.issue", action=t("action.edited"))
                meta = f"#{number} · {repo_name} · {t('card.actor', sender=sender)}"
                body_html = _delta_rows(delta, event_data)
                if "title" in changes:
                    fallback_text = t("fallback.issue_title", number=number, title=title, url=url)
                else:
                    fallback_text = t("fallback.issue_edited", number=number, url=url)
            else:
                action_word = t("action.closed") if action == "closed" else t("action.reopened")
                kicker = t("kicker.issue", action=action_word)
                meta = f"#{number} · {repo_name} · {t('card.actor', sender=sender)}"
                link_text = t("link.issue", number=number, title=title, url=url)
                fallback_text = link_text
        else:
            action_word = t("action.created") if action == "opened" else option("action", action)
            kicker = t("kicker.issue", action=action_word)
            meta = f"#{number} · {repo_name} · {t('card.actor', sender=sender)}"
            body_html = _body_md(body, prefix=_chips(labels), budget=budget) if (labels or body) else ""
            link_text = t("link.issue", number=number, title=title, url=url)
            fallback_text = link_text
        foot = t("card.view_issue")

    elif event_type == "pull_request":
        pr = event_data.get("pull_request", {})
        action = event_data.get("action", "unknown")
        number = pr.get("number", 0)
        title = pr.get("title", "unknown")
        body = pr.get("body", "") or ""
        head_ref = pr.get("head", {}).get("ref", "unknown")
        base_ref = pr.get("base", {}).get("ref", "unknown")
        url = pr.get("html_url", repo_url)
        branch_meta = f"{head_ref} → {base_ref}"

        if compact:
            kind = delta.get("kind")
            if kind == "pr_sync":
                kicker = t("kicker.pr", action=t("action.synchronized"))
                meta = f"#{number} · {branch_meta}"
                body_html = _delta_rows(delta, event_data)
                new_commits = delta.get("new_commits")
                if new_commits:
                    fallback_text = t("fallback.pr_sync", number=number, count=new_commits, url=url)
                elif delta.get("total"):
                    fallback_text = t("fallback.pr_sync_total", number=number,
                                      total=delta["total"], url=url)
                else:
                    fallback_text = t("fallback.pr_edited", number=number, url=url)
            elif kind == "pr_edited":
                changes = delta.get("changes", {}) or {}
                kicker = t("kicker.pr", action=t("action.edited"))
                meta = f"#{number} · {branch_meta}"
                body_html = _delta_rows(delta, event_data)
                if "title" in changes:
                    fallback_text = t("fallback.pr_title", number=number, title=title, url=url)
                else:
                    fallback_text = t("fallback.pr_edited", number=number, url=url)
            else:
                merged = bool(delta.get("merged"))
                action_word = t("action.merged") if merged else t("action.closed")
                kicker = t("kicker.pr", action=action_word)
                meta = f"#{number} · {branch_meta} · {t('card.actor', sender=sender)}"
                if merged:
                    link_text = t("link.pr_merged", number=number, title=title, url=url)
                else:
                    link_text = t("link.pr", number=number, title=title, url=url)
                fallback_text = link_text
        else:
            action_word = option("action", action)
            kicker = t("kicker.pr", action=action_word)
            meta = f"#{number} · {branch_meta} · {t('card.opened_by', sender=sender)}"
            body_html = _body_md(body, budget=budget) if body else ""
            link_text = t("link.pr", number=number, title=title, url=url)
            fallback_text = link_text
        foot = t("card.view_pr")

    elif event_type == "issue_comment":
        issue = event_data.get("issue", {})
        comment = event_data.get("comment", {})
        action = event_data.get("action", "created")
        number = issue.get("number", 0)
        title = issue.get("title", "unknown")
        author = comment.get("user", {}).get("login", sender)
        body = comment.get("body", "") or ""
        kicker = t("kicker.comment", action=t("action.created" if action == "created" else "action.edited"))
        meta = f"#{number} · {repo_name} · {t('card.comment_by', sender=author)}"
        body_html = _body_md(body, budget=budget) if body else ""
        url = comment.get("html_url", issue.get("html_url", repo_url))
        link_text = t("link.issue", number=number, title=title, url=url)
        excerpt = body.strip().split("\n")[0][:40]
        fallback_text = t("fallback.comment", number=number, author=author, excerpt=excerpt, url=url)
        foot = t("card.view_details")

    elif event_type == "pull_request_review":
        pr = event_data.get("pull_request", {})
        review = event_data.get("review", {})
        number = pr.get("number", 0)
        title = pr.get("title", "unknown")
        reviewer = review.get("user", {}).get("login", sender)
        state = (review.get("state", "commented") or "commented").lower()
        verdict = option("action", state)
        body = review.get("body", "") or ""
        kicker = t("kicker.review", verdict=verdict)
        meta = f"#{number} · {repo_name} · {t('card.reviewer', sender=reviewer)}"
        body_html = _body_md(body, budget=budget) if body else ""
        url = review.get("html_url", pr.get("html_url", repo_url))
        link_text = t("link.pr", number=number, title=title, url=url)
        fallback_text = t("fallback.review", number=number, sender=reviewer, verdict=verdict, url=url)
        foot = t("card.view_pr")

    elif event_type == "star":
        count = repo.get("stargazers_count", 0)
        kicker = t("kicker.star")
        title = repo_name
        meta = t("card.star_meta", sender=sender, count=count)
        body_html = ""
        url = repo_url
        link_text = t("link.star", repo=repo_name, sender=sender, url=url)
        fallback_text = link_text
        foot = t("card.view_repo")

    elif event_type == "fork":
        forkee = event_data.get("forkee", {})
        fork_name = forkee.get("full_name", "unknown/repo")
        kicker = t("kicker.fork")
        title = repo_name
        meta = t("card.fork_meta", sender=sender, fork_name=fork_name)
        body_html = ""
        url = forkee.get("html_url", repo_url)
        link_text = t("link.fork", sender=sender, repo=repo_name, url=url)
        fallback_text = link_text
        foot = t("card.view_fork")

    elif event_type == "workflow_run":
        run = event_data.get("workflow_run", {})
        action = event_data.get("action", "completed")
        conclusion = run.get("conclusion", "")
        conclusion_text = option("conclusion", conclusion) if conclusion else option("action", action)
        name = run.get("name", "unknown")
        sha = run.get("head_sha", "")[:7]
        kicker = t("kicker.workflow", conclusion=conclusion_text)
        title = f"{name} (#{run.get('run_number', 0)})"
        meta = f"{repo_name} · {t('tpl.branch')} {run.get('head_branch', 'unknown')} · {sha}"
        head_commit = run.get("head_commit", {})
        commit_message = head_commit.get("message", "").split("\n")[0]
        commit_author = head_commit.get("author", {}).get("name", "unknown")
        body_html = ""
        if commit_message:
            body_html = (
                '<div class="body">'
                f'<div class="p-p">{_esc(commit_message)}</div>'
                f'<div class="p-more">{_esc(commit_author)}</div>'
                "</div>"
            )
        url = run.get("html_url", repo_url)
        link_text = t("link.workflow", name=name, conclusion=conclusion_text, url=url)
        fallback_text = link_text
        foot = t("card.view_details")

    else:
        return None

    kicker_cls = " k-fail" if event_type == "workflow_run" and conclusion == "failure" else ""
    wrap_cls = "wrap compact" if compact else "wrap"
    inner = [
        f'<div class="head"><div class="kicker{kicker_cls}">'
        f'{_esc(kicker)}</div><div class="repo">{_esc(repo_name)}</div></div>',
        f'<div class="title">{_esc(title)}</div>',
        f'<div class="meta">{_esc(meta)}</div>',
        '<div class="rule"></div>',
    ]
    if body_html:
        inner.append(body_html)
    foot_url = _strip_scheme(url)
    foot_html = (
        f'<div class="f-text"><span class="f-label">{_esc(foot)}</span>'
        f'<span class="f-url"> · {_esc(foot_url)}</span></div>'
    )
    qr = _qr_data_url(url)
    if qr:
        foot_html += f'<img class="qr" src="{qr}"/>'
    inner.append(f'<div class="foot">{foot_html}</div>')

    document = f'<div class="{wrap_cls}">{"".join(inner)}</div>'
    return document, link_text, fallback_text


class CardRenderer:

    def __init__(self, sdk, logger):
        self.sdk = sdk
        self.logger = logger
        self._cache = {}

    def _takumi(self):
        try:
            if "Takumi" not in self.sdk.module:
                return None
            return self.sdk.module.get("Takumi")
        except Exception:
            return None

    def available(self):
        return self._takumi() is not None

    def build(self, event_type, event_data, variant="full", delta=None):
        """仅构建卡片 HTML（不渲染 PNG），用于获取兜底短文本。"""
        return build_card(event_type, event_data, variant, delta)

    def render(self, event_type, event_data, variant="full", delta=None):
        built = build_card(event_type, event_data, variant, delta)
        if not built:
            return None
        document, link_text, fallback_text = built
        key = hashlib.md5(document.encode("utf-8")).hexdigest()
        if key in self._cache:
            return self._cache[key], link_text, fallback_text, key
        takumi = self._takumi()
        if takumi is None:
            return None
        try:
            png = takumi.render_html(
                document,
                stylesheets=[CARD_CSS],
                width=CARD_WIDTH,
                height=None,
                lang=get_locale(),
            )
        except Exception as e:
            self.logger.warning(f"渲染卡片失败: {e}")
            return None
        if len(self._cache) > 32:
            self._cache.clear()
        self._cache[key] = png
        return png, link_text, fallback_text, key
