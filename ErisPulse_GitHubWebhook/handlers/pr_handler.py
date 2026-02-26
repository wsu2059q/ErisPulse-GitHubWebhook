from ..utils import truncate_text


class PRHandler:
    """Pull Request 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Pull Request 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        action = event_data.get('action', 'unknown')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        pr = event_data.get('pull_request', {})
        title = pr.get('title', 'unknown')
        number = pr.get('number', 0)
        url = pr.get('html_url', '')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        
        # 获取分支信息
        head = pr.get('head', {})
        base = pr.get('base', {})
        head_ref = head.get('ref', 'unknown')
        base_ref = base.get('ref', 'unknown')
        head_repo = head.get('repo', {}).get('full_name', '')
        
        # 转换 action 为中文
        action_map = {
            'opened': '打开',
            'closed': '关闭',
            'reopened': '重新打开',
            'edited': '编辑',
            'review_requested': '请求审查',
            'review_request_removed': '取消审查请求',
            'ready_for_review': '准备好审查',
            'converted_to_draft': '转为草稿',
            'locked': '锁定',
            'unlocked': '解锁',
        }
        action_cn = action_map.get(action, action)
        
        msg = f"[GitHub] Pull request {action_cn}\n"
        msg += f"仓库: {repo_name}\n"
        msg += f"标题: {title}\n"
        msg += f"发起者: {sender}\n"
        
        # 显示分支信息
        if head_repo and head_repo != repo_name:
            msg += f"分支: {head_repo}:{head_ref} -> {base_ref}\n"
        else:
            msg += f"分支: {head_ref} -> {base_ref}\n"
        
        msg += f"PR #{number}: {url}"
        
        return msg