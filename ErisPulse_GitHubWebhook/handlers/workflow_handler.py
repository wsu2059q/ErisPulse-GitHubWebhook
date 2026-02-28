from ..utils import truncate_text


class WorkflowHandler:
    """GitHub Actions Workflow 事件处理器"""
    
    @staticmethod
    def format_message(event_data):
        """
        格式化 Workflow 构建事件消息
        
        Args:
            event_data: GitHub Webhook 事件数据
        
        Returns:
            str: 格式化后的消息
        """
        action = event_data.get('action', 'completed')
        repo = event_data.get('repository', {})
        repo_name = repo.get('full_name', 'unknown/repo')
        workflow_run = event_data.get('workflow_run', {})
        sender = event_data.get('sender', {}).get('login', 'unknown')
        
        # 获取工作流信息
        workflow_name = workflow_run.get('name', 'unknown')
        workflow_id = workflow_run.get('id', 0)
        status = workflow_run.get('status', 'unknown')
        conclusion = workflow_run.get('conclusion', '')
        run_number = workflow_run.get('run_number', 0)
        
        # 获取分支信息
        head_branch = workflow_run.get('head_branch', 'unknown')
        head_sha = workflow_run.get('head_sha', '')
        head_sha_short = head_sha[:7] if head_sha else 'unknown'
        
        # 获取提交信息
        head_commit = workflow_run.get('head_commit', {})
        commit_message = head_commit.get('message', 'unknown')
        commit_author = head_commit.get('author', {}).get('name', 'unknown')
        
        # 获取时间信息
        created_at = workflow_run.get('created_at', '')
        updated_at = workflow_run.get('updated_at', '')
        
        # 计算耗时
        duration = ''
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
        
        # 获取构建日志和产物链接
        html_url = workflow_run.get('html_url', '')
        logs_url = workflow_run.get('logs_url', '')
        
        # 获取构建产物
        artifacts = workflow_run.get('artifacts', [])
        
        # 转换 action 为中文
        action_map = {
            'requested': '请求',
            'in_progress': '进行中',
            'completed': '完成',
            'queued': '排队中',
        }
        action_cn = action_map.get(action, action)
        
        # 转换 conclusion 为中文
        conclusion_map = {
            'success': '成功',
            'failure': '失败',
            'cancelled': '已取消',
            'timed_out': '超时',
            'action_required': '需要操作',
            'neutral': '中性',
            'skipped': '跳过',
            'stale': '过时',
        }
        conclusion_cn = conclusion_map.get(conclusion, conclusion) if conclusion else status
        
        # 构建消息
        msg = f"[GitHub] Workflow 构建{action_cn}\n"
        msg += f"仓库: {repo_name}\n"
        msg += f"工作流: {workflow_name} (#{run_number})\n"
        
        if conclusion and action == 'completed':
            msg += f"状态: {conclusion_cn}\n"
        else:
            msg += f"状态: {status}\n"
        
        msg += f"分支: {head_branch}\n"
        msg += f"提交: {head_sha_short} - {truncate_text(commit_message)}\n"
        msg += f"提交者: {commit_author}\n"
        
        if duration:
            msg += f"耗时: {duration}\n"
        
        # 添加查看链接
        if html_url:
            msg += f"\n查看详情: {html_url}"
        
        # 添加日志链接（仅当构建失败或完成时）
        if logs_url and action in ['completed', 'failed']:
            msg += f"\n查看日志: {logs_url}"
        
        # 显示构建产物（仅在构建成功时）
        if artifacts and conclusion == 'success' and action == 'completed':
            msg += f"\n\n下载产物 ({len(artifacts)} 个):\n"
            for artifact in artifacts[:3]:
                artifact_name = artifact.get('name', 'unknown')
                artifact_size = artifact.get('size_in_bytes', 0)
                
                # 格式化文件大小
                if artifact_size < 1024:
                    size_str = f"{artifact_size} B"
                elif artifact_size < 1024 * 1024:
                    size_str = f"{artifact_size / 1024:.2f} KB"
                elif artifact_size < 1024 * 1024 * 1024:
                    size_str = f"{artifact_size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{artifact_size / (1024 * 1024 * 1024):.2f} GB"
                
                # 构建产物下载链接
                archive_url = artifact.get('archive_download_url', '')
                if archive_url:
                    msg += f"- {artifact_name} ({size_str})\n"
                    msg += f"  下载链接: {archive_url}\n"
                else:
                    msg += f"- {artifact_name} ({size_str})\n"
            
            if len(artifacts) > 3:
                msg += f"- 还有 {len(artifacts) - 3} 个产物...\n"
        
        return msg