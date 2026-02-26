class StarHandler:
    """Star 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Star 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        action = event_data.get('action', 'created')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        stargazers_count = repo.get('stargazers_count', 0)
        
        msg = f"[GitHub] 仓库被收藏\n"
        msg += f"仓库: {repo_name}\n"
        msg += f"收藏者: {sender}\n"
        msg += f"当前 Star 数: {stargazers_count}"
        
        return msg


class ForkHandler:
    """Fork 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Fork 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        sender = event_data.get('sender', {}).get('login', 'unknown')
        
        # 获取 fork 的仓库信息
        forkee = event_data.get('forkee', {})
        fork_name = forkee.get('full_name', 'unknown/repo')
        fork_url = forkee.get('html_url', '')
        
        msg = f"[GitHub] 仓库被复刻\n"
        msg += f"原仓库: {repo_name}\n"
        msg += f"复刻者: {sender}\n"
        msg += f"复刻仓库: {fork_name}"
        
        if fork_url:
            msg += f"\n查看: {fork_url}"
        
        return msg