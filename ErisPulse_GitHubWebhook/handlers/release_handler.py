from ..utils import truncate_text


class ReleaseHandler:
    """Release 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Release 事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
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
        
        msg = f"[GitHub] Release 发布\n"
        msg += f"仓库: {repo_name}\n"
        msg += f"版本: {tag_name}\n"
        
        if name and name != tag_name:
            msg += f"名称: {name}\n"
        
        msg += f"发布者: {sender}\n"
        
        # 显示版本描述（最多200字符）
        if body:
            msg += f"\n描述: {truncate_text(body, 200)}\n"
        
        # 显示下载链接
        if assets:
            msg += f"\n下载文件 ({len(assets)} 个):\n"
            for asset in assets[:3]:
                asset_name = asset.get('name', 'unknown')
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                size_mb = size / (1024 * 1024)
                msg += f"- {asset_name} ({size_mb:.2f} MB)\n"
            
            if len(assets) > 3:
                msg += f"- 还有 {len(assets) - 3} 个文件...\n"
        
        msg += f"\n查看详情: {url}"
        
        return msg