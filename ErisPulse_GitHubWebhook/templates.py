from typing import Dict, Any


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
        <span>查看 {len(commits)} 个提交</span>
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
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">GitHub Push</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>
    
    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>分支:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{ref}</code>
        </div>
        <div style="font-size: 13px;">
            <strong>推送者:</strong> {pusher}
        </div>
    </div>
    
    {commits_html}
    
    {f'<div style="font-size: 12px; margin-top: 8px;"><a href="{compare_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看对比 →</a></div>' if compare_url else ''}
</div>"""
        
        markdown_lines = [
            "**GitHub Push**",
            "",
            f"**仓库:** {repo_name}",
            f"**分支:** `{ref}`",
            f"**推送者:** {pusher}",
            f"**提交数:** {len(commits)}",
            ""
        ]
        
        if compare_url:
            markdown_lines.append(f"[查看对比]({compare_url})")
        
        text_lines = [
            "GitHub Push",
            "----------",
            f"仓库: {repo_name}",
            f"分支: {ref}",
            f"推送者: {pusher}",
            f"提交数: {len(commits)}",
            ""
        ]
        
        if compare_url:
            text_lines.append(f"查看对比: {compare_url}")
        
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
        
        action_map = {
            'opened': '创建',
            'closed': '关闭',
            'reopened': '重新打开',
            'edited': '编辑',
            'deleted': '删除',
            'pinned': '置顶',
            'unpinned': '取消置顶',
        }
        action_cn = action_map.get(action, action)
        
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
            comments_html = f'<div style="font-size: 12px; margin-top: 8px;"><a href="{comments_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看评论 ({comments}) →</a></div>'
        
        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">GitHub Issue {action_cn}</div>
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
        <strong>操作者:</strong> {sender}
    </div>
    
    {comments_html}
    
    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看 Issue →</a>
    </div>
</div>"""
        
        markdown_lines = [
            f"**GitHub Issue {action_cn}**",
            "",
            f"**仓库:** {repo_name}",
            f"**标题:** {title}",
            f"**编号:** #{number}",
            f"**操作者:** {sender}",
            ""
        ]
        
        if labels:
            label_names = [l.get('name', '') for l in labels]
            markdown_lines.append(f"**标签:** {', '.join(label_names)}")
            markdown_lines.append("")
        
        if comments > 0 and comments_url:
            markdown_lines.append(f"[查看评论]({comments_url})")
            markdown_lines.append("")
        
        markdown_lines.append(f"[查看 Issue]({url})")
        
        text_lines = [
            f"GitHub Issue {action_cn}",
            "----------",
            f"仓库: {repo_name}",
            f"标题: {title}",
            f"编号: #{number}",
            f"操作者: {sender}",
            ""
        ]
        
        if labels:
            label_names = [l.get('name', '') for l in labels]
            text_lines.append(f"标签: {', '.join(label_names)}")
            text_lines.append("")
        
        if comments > 0 and comments_url:
            text_lines.append(f"查看评论: {comments_url}")
            text_lines.append("")
        
        text_lines.append(f"查看 Issue: {url}")
        
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
        review_comments = pr.get('review_comments', 0)
        comments_url = pr.get('comments_url', '')
        
        head = pr.get('head', {})
        base = pr.get('base', {})
        head_ref = head.get('ref', 'unknown')
        base_ref = base.get('ref', 'unknown')
        head_repo = head.get('repo', {}).get('full_name', '')
        
        action_map = {
            'opened': '打开',
            'closed': '关闭',
            'reopened': '重新打开',
            'edited': '编辑',
            'review_requested': '请求审查',
            'ready_for_review': '准备好审查',
        }
        action_cn = action_map.get(action, action)
        
        branch_info = f"{head_ref} → {base_ref}"
        if head_repo and head_repo != repo_name:
            branch_info = f"{head_repo}:{head_ref} → {base_ref}"
        
        comments_html = ""
        if comments > 0 and comments_url:
            comments_html = f'<div style="font-size: 12px; margin-top: 8px;"><a href="{comments_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看评论 ({comments}) →</a></div>'
        
        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">GitHub PR {action_cn}</div>
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
            <strong>分支:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{branch_info}</code>
        </div>
    </div>
    
    <div style="font-size: 13px;">
        <strong>发起者:</strong> {sender}
    </div>
    
    {comments_html}
    
    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看 PR →</a>
    </div>
</div>"""
        
        markdown_lines = [
            f"**GitHub PR {action_cn}**",
            "",
            f"**仓库:** {repo_name}",
            f"**标题:** {title}",
            f"**编号:** #{number}",
            f"**分支:** `{branch_info}`",
            f"**发起者:** {sender}",
            ""
        ]
        
        if comments > 0 and comments_url:
            markdown_lines.append(f"[查看评论]({comments_url})")
            markdown_lines.append("")
        
        markdown_lines.append(f"[查看 PR]({url})")
        
        text_lines = [
            f"GitHub PR {action_cn}",
            "----------",
            f"仓库: {repo_name}",
            f"标题: {title}",
            f"编号: #{number}",
            f"分支: {branch_info}",
            f"发起者: {sender}",
            ""
        ]
        
        if comments > 0 and comments_url:
            text_lines.append(f"查看评论: {comments_url}")
            text_lines.append("")
        
        text_lines.append(f"查看 PR: {url}")
        
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
        
        body_html = ""
        if body:
            body_formatted = body.replace('\n', '<br>')
            body_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.PRIMARY_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>查看版本描述</span>
    </summary>
    <div style="padding: 8px; margin-top: 6px; background: rgba(0, 0, 0, 0.02); border-radius: 4px; font-size: 13px; line-height: 1.6;">
        {body_formatted}
    </div>
</details>"""
        
        assets_html = ""
        if assets:
            assets_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.SUCCESS_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>下载文件 ({len(assets)} 个)</span>
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
                {f'<a href="{download_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none; margin-left: 8px;">下载</a>' if download_url else ''}
            </div>
        </div>
"""
            assets_html += "    </div>\n</details>"
        
        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">GitHub Release 发布</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>
    
    <div style="padding: 10px; background: {cls.SUCCESS_BG}; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 16px; font-weight: bold; color: {cls.SUCCESS_COLOR};">{version_display}</div>
    </div>
    
    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>发布者:</strong> {sender}
    </div>
    
    {body_html}
    
    {assets_html}
    
    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看详情 →</a>
    </div>
</div>"""
        
        markdown_lines = [
            "**GitHub Release 发布**",
            "",
            f"**仓库:** {repo_name}",
            f"**版本:** {version_display}",
            f"**发布者:** {sender}",
            ""
        ]
        
        if assets:
            markdown_lines.append(f"**下载文件 ({len(assets)} 个):**")
            markdown_lines.append("")
            for asset in assets:
                asset_name = asset.get('name', 'unknown')
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                size_mb = size / (1024 * 1024)
                markdown_lines.append(f"- **{asset_name}** ({size_mb:.2f} MB)")
                if download_url:
                    markdown_lines.append(f"  [下载]({download_url})")
            markdown_lines.append("")
        
        markdown_lines.append(f"[查看详情]({url})")
        
        text_lines = [
            "GitHub Release 发布",
            "----------",
            f"仓库: {repo_name}",
            f"版本: {version_display}",
            f"发布者: {sender}",
            ""
        ]
        
        if assets:
            text_lines.append(f"下载文件 ({len(assets)} 个):")
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
        
        text_lines.append(f"查看详情: {url}")
        
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
        <div style="color: {cls.WARNING_COLOR}; font-size: 16px; font-weight: bold;">⭐ GitHub Star</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.WARNING_BG}; border-radius: 12px; font-size: 12px; color: {cls.WARNING_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>
    
    <div style="padding: 10px; background: {cls.WARNING_BG}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px;">
            <strong>收藏者:</strong> {sender}
        </div>
    </div>
    
    <div style="font-size: 13px; color: #666;">
        当前 Star 数: <strong style="color: {cls.WARNING_COLOR};">{stargazers_count}</strong>
    </div>
</div>"""
        
        markdown_lines = [
            "⭐ **GitHub Star**",
            "",
            f"**仓库:** {repo_name}",
            f"**收藏者:** {sender}",
            f"**当前 Star 数:** {stargazers_count}"
        ]
        
        text_lines = [
            "GitHub Star",
            "----------",
            f"仓库: {repo_name}",
            f"收藏者: {sender}",
            f"当前 Star 数: {stargazers_count}"
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
        <div style="color: {cls.PRIMARY_COLOR}; font-size: 16px; font-weight: bold;">🍴 GitHub Fork</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {cls.PRIMARY_BG}; border-radius: 12px; font-size: 12px; color: {cls.PRIMARY_COLOR}; text-decoration: none;">
            {repo_name}
        </a>
    </div>
    
    <div style="padding: 10px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px;">
            <strong>复刻者:</strong> {sender}
        </div>
    </div>
    
    <div style="font-size: 13px; margin-bottom: 8px;">
        <strong>复刻仓库:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{fork_name}</code>
    </div>
    
    {f'<div style="font-size: 12px;"><a href="{fork_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看 →</a></div>' if fork_url else ''}
</div>"""
        
        markdown_lines = [
            "🍴 **GitHub Fork**",
            "",
            f"**原仓库:** {repo_name}",
            f"**复刻者:** {sender}",
            f"**复刻仓库:** `{fork_name}`",
            ""
        ]
        
        if fork_url:
            markdown_lines.append(f"[查看]({fork_url})")
        
        text_lines = [
            "GitHub Fork",
            "----------",
            f"原仓库: {repo_name}",
            f"复刻者: {sender}",
            f"复刻仓库: {fork_name}",
            ""
        ]
        
        if fork_url:
            text_lines.append(f"查看: {fork_url}")
        
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
        sender = event_data.get('sender', {}).get('login', 'unknown')
        
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
                    duration = f"{int(duration_seconds)}秒"
                elif duration_seconds < 3600:
                    minutes = int(duration_seconds // 60)
                    seconds = int(duration_seconds % 60)
                    duration = f"{minutes}分{seconds}秒"
                else:
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    duration = f"{hours}小时{minutes}分"
            except:
                pass
        
        html_url = workflow_run.get('html_url', '')
        logs_url = workflow_run.get('logs_url', '')
        artifacts = workflow_run.get('artifacts', [])
        
        conclusion_map = {
            'success': '成功',
            'failure': '失败',
            'cancelled': '已取消',
            'timed_out': '超时',
            'skipped': '跳过',
        }
        conclusion_cn = conclusion_map.get(conclusion, conclusion) if conclusion else status
        
        status_color = cls.SUCCESS_COLOR if conclusion == 'success' else (cls.ERROR_COLOR if conclusion == 'failure' else cls.PRIMARY_COLOR)
        status_bg = cls.SUCCESS_BG if conclusion == 'success' else (cls.ERROR_BG if conclusion == 'failure' else cls.PRIMARY_BG)
        
        artifacts_html = ""
        if artifacts and conclusion == 'success':
            artifacts_html = f"""
<details>
    <summary style="cursor: pointer; font-size: 13px; padding: 4px 8px; background: {cls.SUCCESS_BG}; border-radius: 4px; display: inline-flex; align-items: center;">
        <span>下载产物 ({len(artifacts)} 个)</span>
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
                {f'<a href="{archive_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none; margin-left: 8px;">下载</a>' if archive_url else ''}
            </div>
        </div>
"""
            artifacts_html += "    </div>\n</details>"
        
        logs_html = ""
        if logs_url and action == 'completed':
            logs_html = f' | <a href="{logs_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看日志 →</a>'
        
        html = f"""<div style="padding: 12px; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: {status_color}; font-size: 16px; font-weight: bold;">⚙️ GitHub Workflow</div>
        <a href="https://github.com/{repo_name}" style="padding: 4px 12px; background: {status_bg}; border-radius: 12px; font-size: 12px; color: {status_color}; text-decoration: none;">
            {repo_name}
        </a>
    </div>
    
    <div style="padding: 10px; background: {status_bg}; border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 4px; color: {status_color};">{workflow_name} (#{run_number})</div>
        <div style="font-size: 13px;">
            <strong>状态:</strong> <span style="color: {status_color}; font-weight: bold;">{conclusion_cn}</span>
        </div>
    </div>
    
    <div style="padding: 8px; background: rgba(0, 0, 0, 0.02); border-radius: 6px; margin-bottom: 8px;">
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>分支:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{head_branch}</code>
        </div>
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>提交:</strong> <code style="background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 3px;">{head_sha_short}</code>
        </div>
        <div style="font-size: 13px; margin-bottom: 4px;">
            <strong>提交信息:</strong> {commit_message}
        </div>
        <div style="font-size: 13px;">
            <strong>提交者:</strong> {commit_author}
        </div>
    </div>
    
    {f'<div style="font-size: 13px;"><strong>耗时:</strong> {duration}</div>' if duration else ''}
    
    {artifacts_html}
    
    <div style="font-size: 12px; margin-top: 8px;">
        <a href="{html_url}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">查看详情 →</a>{logs_html}
    </div>
</div>"""
        
        markdown_lines = [
            "⚙️ **GitHub Workflow**",
            "",
            f"**仓库:** {repo_name}",
            f"**工作流:** {workflow_name} (#{run_number})",
            f"**状态:** {conclusion_cn}",
            f"**分支:** `{head_branch}`",
            f"**提交:** `{head_sha_short}`",
            f"**提交信息:** {commit_message}",
            f"**提交者:** {commit_author}",
            ""
        ]
        
        if duration:
            markdown_lines.append(f"**耗时:** {duration}")
            markdown_lines.append("")
        
        if artifacts and conclusion == 'success':
            markdown_lines.append(f"**下载产物 ({len(artifacts)} 个):**")
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
                    markdown_lines.append(f"  [下载]({archive_url})")
            markdown_lines.append("")
        
        links = f"[查看详情]({html_url})"
        if logs_url and action == 'completed':
            links += f" | [查看日志]({logs_url})"
        markdown_lines.append(links)
        
        text_lines = [
            "GitHub Workflow",
            "----------",
            f"仓库: {repo_name}",
            f"工作流: {workflow_name} (#{run_number})",
            f"状态: {conclusion_cn}",
            f"分支: {head_branch}",
            f"提交: {head_sha_short}",
            f"提交信息: {commit_message}",
            f"提交者: {commit_author}",
            ""
        ]
        
        if duration:
            text_lines.append(f"耗时: {duration}")
            text_lines.append("")
        
        if artifacts and conclusion == 'success':
            text_lines.append(f"下载产物 ({len(artifacts)} 个):")
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
        
        links = f"查看详情: {html_url}"
        if logs_url and action == 'completed':
            links += f"\n查看日志: {logs_url}"
        text_lines.append(links)
        
        return {
            "html": html,
            "markdown": "\n".join(markdown_lines),
            "text": "\n".join(text_lines)
        }