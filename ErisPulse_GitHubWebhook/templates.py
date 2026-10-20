from typing import Dict, Any

from .i18n import t, option
from .utils import markdown_to_html


class GitHubTemplates:
    PRIMARY_COLOR = "#1565c0"
    SUCCESS_COLOR = "#2e7d32"
    WARNING_COLOR = "#e65100"
    ERROR_COLOR = "#b71c1c"

    PRIMARY_BG = "rgba(21, 101, 192, 0.05)"
    SUCCESS_BG = "rgba(76, 175, 80, 0.1)"
    WARNING_BG = "rgba(255, 167, 38, 0.15)"
    ERROR_BG = "rgba(183, 28, 28, 0.1)"

    @classmethod
    def build_push(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        ref = event_data.get('ref', '').replace('refs/heads/', '')
        pusher = event_data.get('pusher', {}).get('name', 'unknown')
        commits = event_data.get('commits', [])
        compare_url = event_data.get('compare', '')

        commits_html = ""
        if commits:
            commits_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.PRIMARY_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>{t('tpl.view_commits', count=len(commits))}</span>
    </summary>
    <div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px;">
"""
            for commit in commits:
                commit_msg = commit.get('message', '')
                commit_id = commit.get('id', '')[:7]
                author = commit.get('author', {}).get('name', 'unknown')
                commits_html += f"""        <div style="margin-bottom: 6px; padding: 6px; background: white; border-radius: 3px; border-left: 3px solid {cls.PRIMARY_COLOR};">
            <div style="font-size: 13px; font-weight: bold; margin-bottom: 4px;">{commit_msg}</div>
            <div style="font-size: 12px; color: #666;">
                <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 4px; border-radius: 2px;">{commit_id}</code>
                <span style="margin-left: 8px;">{author}</span>
            </div>
        </div>
"""
            commits_html += "    </div>\n</details>"

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">{t('tpl.push')}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>{t('tpl.branch')}:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{ref}</code>
        </div>
        <div style="font-size: 13px;">
            <strong>{t('tpl.pusher')}:</strong> {pusher}
        </div>
    </div>

    {commits_html}

    {f'<div style="font-size: 12px; margin-top: 8px;"><a href="{compare_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t("card.view_compare")} →</a></div>' if compare_url else ''}
</div>"""

        markdown_lines = [
            f"**{t('tpl.push')}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.branch')}:** `{ref}`",
            f"**{t('tpl.pusher')}:** {pusher}",
            f"**{t('tpl.commit_count')}:** {len(commits)}",
            ""
        ]

        if compare_url:
            markdown_lines.append(f"[{t('card.view_compare')}]({compare_url})")

        text_lines = [
            t('tpl.push'),
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.branch')}: {ref}",
            f"{t('tpl.pusher')}: {pusher}",
            f"{t('tpl.commit_count')}: {len(commits)}",
            ""
        ]

        if compare_url:
            text_lines.append(f"{t('card.view_compare')}: {compare_url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_issues(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        action = event_data.get('action', 'unknown')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        issue = event_data.get('issue', {})
        title = issue.get('title', 'unknown')
        number = issue.get('number', 0)
        url = issue.get('html_url', '')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        labels = issue.get('labels', [])
        comments = issue.get('comments', 0)
        comments_url = issue.get('comments_url', '')

        action_word = t('action.created') if action == 'opened' else option('action', action)

        labels_html = ""
        if labels:
            labels_html = '<div style="margin-top: 8px;">'
            for label in labels:
                label_name = label.get('name', '')
                label_color = label.get('color', 'CCCCCC')
                labels_html += f'<span style="display: inline-block; font-size: 11px; padding: 2px 6px; margin-right: 4px; margin-bottom: 4px; background: #{label_color}; color: white; border-radius: 3px;">{label_name}</span>'
            labels_html += '</div>'

        comments_html = ""
        if comments > 0 and comments_url:
            comments_html = f'<div style="font-size: 12px; margin-top: 8px;"><a href="{comments_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t("tpl.view_comments", count=comments)} →</a></div>'

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">{t('tpl.issue', action=action_word)}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 6px;">{title}</div>
        <div style="font-size: 13px; color: #666;">#{number}</div>
    </div>

    {labels_html}

    <div style="font-size: 13px; margin-top: 8px;">
        <strong>{t('tpl.actor')}:</strong> {sender}
    </div>

    {comments_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_issue')} →</a>
    </div>
</div>"""

        markdown_lines = [
            f"**{t('tpl.issue', action=action_word)}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.title')}:** {title}",
            f"**{t('tpl.number')}:** #{number}",
            f"**{t('tpl.actor')}:** {sender}",
            ""
        ]

        if labels:
            label_names = [l.get('name', '') for l in labels]
            markdown_lines.append(f"**{t('card.labels')}:** {', '.join(label_names)}")
            markdown_lines.append("")

        if comments > 0 and comments_url:
            markdown_lines.append(f"[{t('tpl.view_comments', count=comments)}]({comments_url})")
            markdown_lines.append("")

        markdown_lines.append(f"[{t('card.view_issue')}]({url})")

        text_lines = [
            t('tpl.issue', action=action_word),
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.title')}: {title}",
            f"{t('tpl.number')}: #{number}",
            f"{t('tpl.actor')}: {sender}",
            ""
        ]

        if labels:
            label_names = [l.get('name', '') for l in labels]
            text_lines.append(f"{t('card.labels')}: {', '.join(label_names)}")
            text_lines.append("")

        if comments > 0 and comments_url:
            text_lines.append(f"{t('tpl.view_comments', count=comments)}: {comments_url}")
            text_lines.append("")

        text_lines.append(f"{t('card.view_issue')}: {url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_pr(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        action = event_data.get('action', 'unknown')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        pr = event_data.get('pull_request', {})
        title = pr.get('title', 'unknown')
        number = pr.get('number', 0)
        url = pr.get('html_url', '')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        comments = pr.get('comments', 0)
        comments_url = pr.get('comments_url', '')

        head = pr.get('head', {})
        base = pr.get('base', {})
        head_ref = head.get('ref', 'unknown')
        base_ref = base.get('ref', 'unknown')
        head_repo = head.get('repo', {}).get('full_name', '')

        action_word = option('action', action)

        branch_info = f"{head_ref} → {base_ref}"
        if head_repo and head_repo != repo_name:
            branch_info = f"{head_repo}:{head_ref} → {base_ref}"

        comments_html = ""
        if comments > 0 and comments_url:
            comments_html = f'<div style="font-size: 12px; margin-top: 8px;"><a href="{comments_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t("tpl.view_comments", count=comments)} →</a></div>'

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">{t('tpl.pr', action=action_word)}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 6px;">{title}</div>
        <div style="font-size: 13px; color: #666;">#{number}</div>
    </div>

    <div style="padding: 8px; background: rgba(0, 0, 0, 0.02); border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 13px;">
            <strong>{t('tpl.branch')}:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{branch_info}</code>
        </div>
    </div>

    <div style="font-size: 13px;">
        <strong>{t('tpl.starter')}:</strong> {sender}
    </div>

    {comments_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_pr')} →</a>
    </div>
</div>"""

        markdown_lines = [
            f"**{t('tpl.pr', action=action_word)}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.title')}:** {title}",
            f"**{t('tpl.number')}:** #{number}",
            f"**{t('tpl.branch')}:** `{branch_info}`",
            f"**{t('tpl.starter')}:** {sender}",
            ""
        ]

        if comments > 0 and comments_url:
            markdown_lines.append(f"[{t('tpl.view_comments', count=comments)}]({comments_url})")
            markdown_lines.append("")

        markdown_lines.append(f"[{t('card.view_pr')}]({url})")

        text_lines = [
            t('tpl.pr', action=action_word),
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.title')}: {title}",
            f"{t('tpl.number')}: #{number}",
            f"{t('tpl.branch')}: {branch_info}",
            f"{t('tpl.starter')}: {sender}",
            ""
        ]

        if comments > 0 and comments_url:
            text_lines.append(f"{t('tpl.view_comments', count=comments)}: {comments_url}")
            text_lines.append("")

        text_lines.append(f"{t('card.view_pr')}: {url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_release(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        action = event_data.get('action', 'published')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        release = event_data.get('release', {})
        tag_name = release.get('tag_name', 'unknown')
        name = release.get('name', '')
        url = release.get('html_url', '')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        body = release.get('body', '')
        assets = release.get('assets', [])

        version_display = tag_name
        if name and name != tag_name:
            version_display = f"{name} ({tag_name})"

        title_word = t('tpl.release') if action != 'edited' else t('kicker.release_changelog')

        body_html = ""
        if body:
            body_parsed = markdown_to_html(body)
            body_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.PRIMARY_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>{t('tpl.view_desc')}</span>
    </summary>
    <div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px; line-height: 1.6;">
        {body_parsed}
    </div>
</details>"""

        assets_html = ""
        if assets:
            assets_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.SUCCESS_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>{t('tpl.download_files', count=len(assets))}</span>
    </summary>
    <div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px;">
"""
            for asset in assets:
                asset_name = asset.get('name', 'unknown')
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                size_mb = size / (1024 * 1024)
                assets_html += f"""        <div style="margin-bottom: 6px; padding: 6px; background: white; border-radius: 3px; border-left: 3px solid {cls.SUCCESS_COLOR};">
            <div style="font-size: 13px; font-weight: bold; margin-bottom: 4px;">{asset_name}</div>
            <div style="font-size: 12px; color: #666;">
                <span>{size_mb:.2f} MB</span>
                {f'<a href="{download_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none; margin-left: 8px;">{t("tpl.download")}</a>' if download_url else ''}
            </div>
        </div>
"""
            assets_html += "    </div>\n</details>"

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">{title_word}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.SUCCESS_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 16px; font-weight: bold; color: {cls.SUCCESS_COLOR};">{version_display}</div>
    </div>

    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>{t('tpl.publisher')}:</strong> {sender}
    </div>

    {body_html}

    {assets_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_details')} →</a>
    </div>
</div>"""

        markdown_lines = [
            f"**{title_word}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.version')}:** {version_display}",
            f"**{t('tpl.publisher')}:** {sender}",
            ""
        ]

        if body:
            markdown_lines.append(body)
            markdown_lines.append("")

        if assets:
            markdown_lines.append(f"**{t('tpl.download_files', count=len(assets))}:**")
            markdown_lines.append("")
            for asset in assets:
                asset_name = asset.get('name', 'unknown')
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                size_mb = size / (1024 * 1024)
                markdown_lines.append(f"- **{asset_name}** ({size_mb:.2f} MB)")
                if download_url:
                    markdown_lines.append(f"  [{t('tpl.download')}]({download_url})")
            markdown_lines.append("")

        markdown_lines.append(f"[{t('card.view_details')}]({url})")

        text_lines = [
            title_word,
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.version')}: {version_display}",
            f"{t('tpl.publisher')}: {sender}",
            ""
        ]

        if body:
            text_lines.append(body)
            text_lines.append("")

        if assets:
            text_lines.append(f"{t('tpl.download_files', count=len(assets))}:")
            text_lines.append("")
            for asset in assets:
                asset_name = asset.get('name', 'unknown')
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                size_mb = size / (1024 * 1024)
                text_lines.append(f"- {asset_name} ({size_mb:.2f} MB)")
                if download_url:
                    text_lines.append(f"  {download_url}")
            text_lines.append("")

        text_lines.append(f"{t('card.view_details')}: {url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_star(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        stargazers_count = repo.get('stargazers_count', 0)

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.WARNING_COLOR}; font-size: 16px; font-weight: bold;">⭐ {t('tpl.star')}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.WARNING_BG}; border-radius: 12px; font-size: 12px; color: {cls.WARNING_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.WARNING_BG}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px;">
            <strong>{t('tpl.stargazer')}:</strong> {sender}
        </div>
    </div>

    <div style="font-size: 13px; color: #666;">
        {t('tpl.star_total')}: <strong style="color: {cls.WARNING_COLOR};">{stargazers_count}</strong>
    </div>
</div>"""

        markdown_lines = [
            f"⭐ **{t('tpl.star')}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.stargazer')}:** {sender}",
            f"**{t('tpl.star_total')}:** {stargazers_count}"
        ]

        text_lines = [
            t('tpl.star'),
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.stargazer')}: {sender}",
            f"{t('tpl.star_total')}: {stargazers_count}"
        ]

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_fork(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        sender = event_data.get('sender', {}).get('login', 'unknown')

        forkee = event_data.get('forkee', {})
        fork_name = forkee.get('full_name', 'unknown/repo')
        fork_url = forkee.get('html_url', '')

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">🍴 {t('tpl.fork')}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px;">
            <strong>{t('tpl.forker')}:</strong> {sender}
        </div>
    </div>

    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>{t('tpl.fork_repo')}:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{fork_name}</code>
    </div>

    {f'<div style="font-size: 12px;"><a href="{fork_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t("tpl.view")} →</a></div>' if fork_url else ''}
</div>"""

        markdown_lines = [
            f"🍴 **{t('tpl.fork')}**",
            "",
            f"**{t('tpl.origin_repo')}:** {repo_name}",
            f"**{t('tpl.forker')}:** {sender}",
            f"**{t('tpl.fork_repo')}:** `{fork_name}`",
            ""
        ]

        if fork_url:
            markdown_lines.append(f"[{t('tpl.view')}]({fork_url})")

        text_lines = [
            t('tpl.fork'),
            "----------",
            f"{t('tpl.origin_repo')}: {repo_name}",
            f"{t('tpl.forker')}: {sender}",
            f"{t('tpl.fork_repo')}: {fork_name}",
            ""
        ]

        if fork_url:
            text_lines.append(f"{t('tpl.view')}: {fork_url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_workflow(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        action = event_data.get('action', 'completed')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        workflow_run = event_data.get('workflow_run', {})

        workflow_name = workflow_run.get('name', 'unknown')
        run_number = workflow_run.get('run_number', 0)
        status = workflow_run.get('status', 'unknown')
        conclusion = workflow_run.get('conclusion', '')
        head_branch = workflow_run.get('head_branch', 'unknown')
        head_sha = workflow_run.get('head_sha', '')
        head_sha_short = head_sha[:7] if head_sha else 'unknown'

        head_commit = workflow_run.get('head_commit', {})
        commit_message = head_commit.get('message', 'unknown')
        commit_author = head_commit.get('author', {}).get('name', 'unknown')

        duration = ''
        created_at = workflow_run.get('created_at', '')
        updated_at = workflow_run.get('updated_at', '')
        if created_at and updated_at:
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                duration_seconds = (end_time - start_time).total_seconds()

                if duration_seconds < 60:
                    duration = t("duration.sec", s=int(duration_seconds))
                elif duration_seconds < 3600:
                    minutes = int(duration_seconds // 60)
                    seconds = int(duration_seconds % 60)
                    duration = t("duration.min", m=minutes, s=seconds)
                else:
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    duration = t("duration.hour", h=hours, m=minutes)
            except:
                pass

        html_url = workflow_run.get('html_url', '')
        logs_url = workflow_run.get('logs_url', '')
        artifacts = workflow_run.get('artifacts', [])

        conclusion_word = option('conclusion', conclusion) if conclusion else option('action', action, fallback=status)

        status_color = cls.SUCCESS_COLOR if conclusion == 'success' else (cls.ERROR_COLOR if conclusion == 'failure' else cls.PRIMARY_COLOR)
        status_bg = cls.SUCCESS_BG if conclusion == 'success' else (cls.ERROR_BG if conclusion == 'failure' else cls.PRIMARY_BG)

        artifacts_html = ""
        if artifacts and conclusion == 'success':
            artifacts_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.SUCCESS_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>{t('tpl.download_artifacts', count=len(artifacts))}</span>
    </summary>
    <div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px;">
"""
            for artifact in artifacts:
                artifact_name = artifact.get('name', 'unknown')
                artifact_size = artifact.get('size_in_bytes', 0)
                archive_url = artifact.get('archive_download_url', '')

                if artifact_size < 1024 * 1024:
                    size_str = f"{artifact_size / 1024:.2f} KB"
                elif artifact_size < 1024 * 1024 * 1024:
                    size_str = f"{artifact_size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{artifact_size / (1024 * 1024 * 1024):.2f} GB"

                artifacts_html += f"""        <div style="margin-bottom: 6px; padding: 6px; background: white; border-radius: 3px; border-left: 3px solid {cls.SUCCESS_COLOR};">
            <div style="font-size: 13px; font-weight: bold; margin-bottom: 4px;">{artifact_name}</div>
            <div style="font-size: 12px; color: #666;">
                <span>{size_str}</span>
                {f'<a href="{archive_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none; margin-left: 8px;">{t("tpl.download")}</a>' if archive_url else ''}
            </div>
        </div>
"""
            artifacts_html += "    </div>\n</details>"

        logs_html = ""
        if logs_url and action == 'completed':
            logs_html = f' | <a href="{logs_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t("tpl.view_logs")} →</a>'

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {status_color}; font-size: 16px; font-weight: bold;">⚙️ {t('tpl.workflow')}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {status_bg}; border-radius: 12px; font-size: 12px; color: {status_color}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {status_bg}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 4px; color: {status_color};">{workflow_name} (#{run_number})</div>
        <div style="font-size: 13px;">
            <strong>{t('tpl.status')}:</strong> <span style="color: {status_color}; font-weight: bold;">{conclusion_word}</span>
        </div>
    </div>

    <div style="padding: 8px; background: rgba(0, 0, 0, 0.02); border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>{t('tpl.branch')}:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{head_branch}</code>
        </div>
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>{t('tpl.commit')}:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{head_sha_short}</code>
        </div>
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>{t('tpl.commit_msg')}:</strong> {commit_message}
        </div>
        <div style="font-size: 13px;">
            <strong>{t('tpl.committer')}:</strong> {commit_author}
        </div>
    </div>

    {f'<div style="font-size: 13px;"><strong>{t("tpl.duration")}:</strong> {duration}</div>' if duration else ''}

    {artifacts_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{html_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_details')} →</a>{logs_html}
    </div>
</div>"""

        markdown_lines = [
            f"⚙️ **{t('tpl.workflow')}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**{t('tpl.workflow_name')}:** {workflow_name} (#{run_number})",
            f"**{t('tpl.status')}:** {conclusion_word}",
            f"**{t('tpl.branch')}:** `{head_branch}`",
            f"**{t('tpl.commit')}:** `{head_sha_short}`",
            f"**{t('tpl.commit_msg')}:** {commit_message}",
            f"**{t('tpl.committer')}:** {commit_author}",
            ""
        ]

        if duration:
            markdown_lines.append(f"**{t('tpl.duration')}:** {duration}")
            markdown_lines.append("")

        if artifacts and conclusion == 'success':
            markdown_lines.append(f"**{t('tpl.download_artifacts', count=len(artifacts))}:**")
            markdown_lines.append("")
            for artifact in artifacts:
                artifact_name = artifact.get('name', 'unknown')
                artifact_size = artifact.get('size_in_bytes', 0)
                archive_url = artifact.get('archive_download_url', '')

                if artifact_size < 1024 * 1024:
                    size_str = f"{artifact_size / 1024:.2f} KB"
                elif artifact_size < 1024 * 1024 * 1024:
                    size_str = f"{artifact_size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{artifact_size / (1024 * 1024 * 1024):.2f} GB"

                markdown_lines.append(f"- **{artifact_name}** ({size_str})")
                if archive_url:
                    markdown_lines.append(f"  [{t('tpl.download')}]({archive_url})")
            markdown_lines.append("")

        links = f"[{t('card.view_details')}]({html_url})"
        if logs_url and action == 'completed':
            links += f" | [{t('tpl.view_logs')}]({logs_url})"
        markdown_lines.append(links)

        text_lines = [
            t('tpl.workflow'),
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"{t('tpl.workflow_name')}: {workflow_name} (#{run_number})",
            f"{t('tpl.status')}: {conclusion_word}",
            f"{t('tpl.branch')}: {head_branch}",
            f"{t('tpl.commit')}: {head_sha_short}",
            f"{t('tpl.commit_msg')}: {commit_message}",
            f"{t('tpl.committer')}: {commit_author}",
            ""
        ]

        if duration:
            text_lines.append(f"{t('tpl.duration')}: {duration}")
            text_lines.append("")

        if artifacts and conclusion == 'success':
            text_lines.append(f"{t('tpl.download_artifacts', count=len(artifacts))}:")
            text_lines.append("")
            for artifact in artifacts:
                artifact_name = artifact.get('name', 'unknown')
                artifact_size = artifact.get('size_in_bytes', 0)
                archive_url = artifact.get('archive_download_url', '')

                if artifact_size < 1024 * 1024:
                    size_str = f"{artifact_size / 1024:.2f} KB"
                elif artifact_size < 1024 * 1024 * 1024:
                    size_str = f"{artifact_size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{artifact_size / (1024 * 1024 * 1024):.2f} GB"

                text_lines.append(f"- {artifact_name} ({size_str})")
                if archive_url:
                    text_lines.append(f"  {archive_url}")
            text_lines.append("")

        links = f"{t('card.view_details')}: {html_url}"
        if logs_url and action == 'completed':
            links += f"\n{t('tpl.view_logs')}: {logs_url}"
        text_lines.append(links)

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_comment(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        action = event_data.get('action', 'created')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        issue = event_data.get('issue', {})
        comment = event_data.get('comment', {})
        title = issue.get('title', 'unknown')
        number = issue.get('number', 0)
        url = comment.get('html_url', issue.get('html_url', ''))
        author = comment.get('user', {}).get('login', 'unknown')
        body = comment.get('body', '') or ''

        action_word = t('action.created') if action == 'created' else t('action.edited')
        body_display = body[:1000]

        comments_html = ""
        if body_display:
            comments_html = f'<div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px; font-size: 13px; line-height: 1.6;">{markdown_to_html(body_display)}</div>'

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">{t('tpl.comment')} · {action_word}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 6px;">{title}</div>
        <div style="font-size: 13px; color: #666;">#{number}</div>
    </div>

    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>{t('tpl.commenter')}:</strong> {author}
    </div>

    {comments_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_details')} →</a>
    </div>
</div>"""

        markdown_lines = [
            f"**{t('tpl.comment')} · {action_word}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**#{number} {title}**",
            f"**{t('tpl.commenter')}:** {author}",
            "",
            body_display,
            "",
            f"[{t('card.view_details')}]({url})",
        ]

        text_lines = [
            f"{t('tpl.comment')} · {action_word}",
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"#{number} {title}",
            f"{t('tpl.commenter')}: {author}",
            "",
            body_display,
            "",
            f"{t('card.view_details')}: {url}",
        ]

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }

    @classmethod
    def build_review(cls, event_data: Dict[str, Any]) -> Dict[str, str]:
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        pr = event_data.get('pull_request', {})
        review = event_data.get('review', {})
        title = pr.get('title', 'unknown')
        number = pr.get('number', 0)
        url = review.get('html_url', pr.get('html_url', ''))
        reviewer = review.get('user', {}).get('login', 'unknown')
        state = (review.get('state', 'commented') or 'commented').lower()
        body = review.get('body', '') or ''

        verdict = option('action', state)
        status_color = cls.SUCCESS_COLOR if state == 'approved' else (cls.ERROR_COLOR if state == 'changes_requested' else cls.PRIMARY_COLOR)
        status_bg = cls.SUCCESS_BG if state == 'approved' else (cls.ERROR_BG if state == 'changes_requested' else cls.PRIMARY_BG)

        body_html = ""
        if body:
            body_html = f'<div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px; font-size: 13px; line-height: 1.6;">{markdown_to_html(body[:1000])}</div>'

        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {status_color}; font-size: 16px; font-weight: bold;">{t('tpl.review')} · {verdict}</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {status_bg}; border-radius: 12px; font-size: 12px; color: {status_color}; text-decoration: none;">
            {repo_name}
        </a>
    </div>

    <div style="padding: 10px; background: {status_bg}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 6px;">{title}</div>
        <div style="font-size: 13px; color: #666;">#{number}</div>
    </div>

    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>{t('tpl.reviewer')}:</strong> {reviewer}
    </div>

    {body_html}

    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{t('card.view_pr')} →</a>
    </div>
</div>"""

        markdown_lines = [
            f"**{t('tpl.review')} · {verdict}**",
            "",
            f"**{t('tpl.repo')}:** {repo_name}",
            f"**#{number} {title}**",
            f"**{t('tpl.reviewer')}:** {reviewer}",
            "",
        ]

        text_lines = [
            f"{t('tpl.review')} · {verdict}",
            "----------",
            f"{t('tpl.repo')}: {repo_name}",
            f"#{number} {title}",
            f"{t('tpl.reviewer')}: {reviewer}",
            "",
        ]

        if body:
            markdown_lines.append(body[:1000])
            markdown_lines.append("")
            text_lines.append(body[:1000])
            text_lines.append("")

        markdown_lines.append(f"[{t('card.view_pr')}]({url})")
        text_lines.append(f"{t('card.view_pr')}: {url}")

        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }
