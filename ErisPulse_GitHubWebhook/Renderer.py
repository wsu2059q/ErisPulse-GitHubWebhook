import base64
import hashlib
import html
import io
import re

CARD_WIDTH = 880
BODY_BUDGET = 2500
COMMIT_LIMIT = 6
QR_SIZE = 132

ACCENT = "#ff3366"
MUTED = "#6b7280"

CARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Roboto", "Noto Sans SC", sans-serif; }
.wrap { background: #ffffff; padding: 56px 56px 48px; }
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


def _body_md(md_text, prefix=""):
    source, truncated = _fit_text(md_text)
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
            dash = "–&nbsp; "
            if list_match.group(1):
                parts.append(f'<div class="p-li2">{dash}{_inline(list_match.group(2))}</div>')
            else:
                parts.append(f'<div class="p-li">{dash}{_inline(list_match.group(2))}</div>')
            continue
        if not stripped:
            continue
        parts.append(f'<div class="p-p">{_inline(stripped)}</div>')
    if truncated:
        parts.append('<div class="p-more">…… 内容较长，已截断</div>')
    if not parts:
        return ""
    return f'<div class="body">{"".join(parts)}</div>'


def _chips(labels):
    if not labels:
        return ""
    names = " · ".join(l.get("name", "") for l in labels)
    return f'<div class="tags"><span class="t-muted">标签&nbsp;&nbsp;</span>{_esc(names)}</div>'


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
        rows.append(f'<div class="p-more">…… 共 {len(commits)} 个提交</div>')
    return f'<div class="body">{"".join(rows)}</div>'


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


def build_card(event_type, event_data):
    repo = event_data.get("repository", {})
    repo_name = repo.get("full_name", "unknown/repo")
    repo_url = f"https://github.com/{repo_name}"
    sender = event_data.get("sender", {}).get("login", "unknown")

    if event_type == "release":
        release = event_data.get("release", {})
        tag = release.get("tag_name", "unknown")
        name = release.get("name", "")
        version = f"{name} ({tag})" if name and name != tag else tag
        body = release.get("body", "")
        published = _date(release.get("published_at", ""))
        kicker = "Release"
        title = version
        meta = f"{repo_name} · 发布者 {sender}" + (f" · {published}" if published else "")
        body_html = _body_md(body)
        url = release.get("html_url", repo_url)
        link_text = f"🚀 {version} 已发布\n{url}"
        foot = "查看详情"

    elif event_type == "push":
        branch = event_data.get("ref", "").replace("refs/heads/", "")
        pusher = event_data.get("pusher", {}).get("name", "unknown")
        commits = event_data.get("commits", [])
        compare = event_data.get("compare", "")
        kicker = "Push"
        title = f"{branch} 分支有 {len(commits)} 个新提交"
        meta = f"{repo_name} · 推送者 {pusher}"
        body_html = _commits_body(commits)
        url = compare or repo_url
        link_text = f"Push：{branch}（{len(commits)} 个提交）\n{url}"
        foot = "查看对比" if compare else "查看仓库"

    elif event_type == "issues":
        issue = event_data.get("issue", {})
        action = event_data.get("action", "unknown")
        action_map = {
            "opened": "创建", "closed": "关闭", "reopened": "重新打开",
            "edited": "编辑", "pinned": "置顶",
        }
        kicker = f"Issue · {action_map.get(action, action)}"
        title = issue.get("title", "unknown")
        meta = f"#{issue.get('number', 0)} · {repo_name} · 操作者 {sender}"
        body = issue.get("body", "") or ""
        labels = issue.get("labels", [])
        body_html = _body_md(body, prefix=_chips(labels)) if (labels or body) else ""
        url = issue.get("html_url", repo_url)
        link_text = f"#{issue.get('number', 0)} {title}\n{url}"
        foot = "查看 Issue"

    elif event_type == "pull_request":
        pr = event_data.get("pull_request", {})
        action = event_data.get("action", "unknown")
        action_map = {
            "opened": "打开", "closed": "关闭", "reopened": "重新打开",
            "ready_for_review": "待审查",
        }
        head_ref = pr.get("head", {}).get("ref", "unknown")
        base_ref = pr.get("base", {}).get("ref", "unknown")
        kicker = f"Pull Request · {action_map.get(action, action)}"
        title = pr.get("title", "unknown")
        meta = f"#{pr.get('number', 0)} · {head_ref} → {base_ref} · 发起者 {sender}"
        body = pr.get("body", "") or ""
        body_html = _body_md(body) if body else ""
        url = pr.get("html_url", repo_url)
        link_text = f"#{pr.get('number', 0)} {title}\n{url}"
        foot = "查看 PR"

    elif event_type == "star":
        count = repo.get("stargazers_count", 0)
        kicker = "Star"
        title = repo_name
        meta = f"{sender} 加了星 · 当前累计 {count} 颗星"
        body_html = ""
        url = repo_url
        link_text = f"⭐ {repo_name} 收到来自 {sender} 的 Star\n{url}"
        foot = "查看仓库"

    elif event_type == "fork":
        forkee = event_data.get("forkee", {})
        fork_name = forkee.get("full_name", "unknown/repo")
        kicker = "Fork"
        title = repo_name
        meta = f"{sender} 复刻至 {fork_name}"
        body_html = ""
        url = forkee.get("html_url", repo_url)
        link_text = f"🍴 {sender} 复刻了 {repo_name}\n{url}"
        foot = "查看复刻"

    elif event_type == "workflow_run":
        run = event_data.get("workflow_run", {})
        action = event_data.get("action", "completed")
        conclusion = run.get("conclusion", "")
        conclusion_map = {
            "success": "成功", "failure": "失败", "cancelled": "已取消",
            "timed_out": "超时", "skipped": "跳过",
        }
        conclusion_cn = conclusion_map.get(conclusion, conclusion) if conclusion else action
        name = run.get("name", "unknown")
        sha = run.get("head_sha", "")[:7]
        kicker = f"Workflow · {conclusion_cn}"
        title = f"{name} (#{run.get('run_number', 0)})"
        meta = f"{repo_name} · 分支 {run.get('head_branch', 'unknown')} · {sha}"
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
        link_text = f"⚙️ Workflow {name}：{conclusion_cn}\n{url}"
        foot = "查看详情"

    else:
        return None

    kicker_cls = " k-fail" if event_type == "workflow_run" and conclusion == "failure" else ""
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

    document = f'<div class="wrap">{"".join(inner)}</div>'
    return document, link_text


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

    def render(self, event_type, event_data):
        built = build_card(event_type, event_data)
        if not built:
            return None
        document, link_text = built
        key = hashlib.md5(document.encode("utf-8")).hexdigest()
        if key in self._cache:
            return self._cache[key], link_text
        takumi = self._takumi()
        if takumi is None:
            return None
        try:
            png = takumi.render_html(
                document,
                stylesheets=[CARD_CSS],
                width=CARD_WIDTH,
                height=None,
                lang="zh-CN",
            )
        except Exception as e:
            self.logger.warning(f"渲染卡片失败: {e}")
            return None
        if len(self._cache) > 32:
            self._cache.clear()
        self._cache[key] = png
        return png, link_text
