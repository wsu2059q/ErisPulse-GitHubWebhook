from ..utils import truncate_text


class IssuesHandler:
    """Issues 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Issues 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        action = event_data.get('action', 'unknown')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        issue = event_data.get('issue', {})
        title = issue.get('title', 'unknown')
        number = issue.get('number', 0)
        url = issue.get('html_url', '')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        
        # 转换 action 为中文
        action_map = {
            'opened': '创建',
            'closed': '关闭',
            'reopened': '重新打开',
            'edited': '编辑',
            'deleted': '删除',
            'pinned': '置顶',
            'unpinned': '取消置顶',
            'transferred': '转移',
        }
        action_cn = action_map.get(action, action)
        
        msg = f"[GitHub] Issue {action_cn}\n"
        msg += f"仓库: {repo_name}\n"
        msg += f"标题: {title}\n"
        msg += f"操作者: {sender}\n"
        msg += f"Issue #{number}: {url}"
        
        return msg