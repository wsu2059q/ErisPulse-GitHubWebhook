from ..utils import truncate_text


class PushHandler:
    """Push 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Push 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        ref = event_data.get('ref', '').replace('refs/heads/', '')
        pusher = event_data.get('pusher', {}).get('name', 'unknown')
        commits = event_data.get('commits', [])
        
        msg = f"[GitHub] Push 到 {repo_name}\n"
        msg += f"分支: {ref}\n"
        msg += f"推送者: {pusher}\n"
        msg += f"提交数: {len(commits)}\n\n"
        
        # 显示提交信息（最多5条）
        for commit in commits[:5]:
            commit_msg = commit.get('message', '')
            commit_id = commit.get('id', '')[:7]
            msg += f"- {truncate_text(commit_msg)} ({commit_id})\n"
        
        # 如果有更多提交
        if len(commits) > 5:
            msg += f"\n还有 {len(commits) - 5} 条提交未显示...\n"
        
        # 添加对比链接
        compare_url = event_data.get('compare', '')
        if compare_url:
            msg += f"\n查看对比: {compare_url}"
        
        return msg