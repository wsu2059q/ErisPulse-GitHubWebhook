import hashlib
import hmac
import uuid
from datetime import datetime


def generate_uuid_short(length=4):
    """生成短 UUID"""
    return uuid.uuid4().hex[:length]


def verify_signature(payload, signature, secret):
    """
    验证 GitHub Webhook 签名
    
    Args:
        payload: 请求体（bytes）
        signature: 请求头中的签名（格式: sha256=...）
        secret: Webhook 密钥
    
    Returns:
        bool: 签名是否有效
    """
    if not signature or not secret:
        return False
    
    if not signature.startswith('sha256='):
        return False
    
    hash_algorithm, github_signature = signature.split('=', 1)
    
    # 计算 HMAC-SHA256
    mac = hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    # 使用恒定时间比较防止时序攻击
    return hmac.compare_digest(expected_signature, github_signature)


def format_timestamp(timestamp):
    """格式化时间戳"""
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate_text(text, max_length=50):
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def get_event_key(repo, event_type, event_data):
    """
    生成事件唯一标识
    
    Args:
        repo: 仓库名称
        event_type: 事件类型
        event_data: 事件数据
    
    Returns:
        str: 事件唯一键
    """
    if event_type == 'push':
        # 使用最新的 commit id
        head_commit = event_data.get('head_commit', {})
        commit_id = head_commit.get('id', event_data.get('after', ''))
        return f"{repo}:push:{commit_id}"
    
    elif event_type in ['issues', 'pull_request']:
        # 使用 issue/PR 的 number 和 action
        number = event_data.get('number', '')
        action = event_data.get('action', '')
        return f"{repo}:{event_type}:{number}:{action}"
    
    elif event_type == 'release':
        # 使用 tag 名称
        tag_name = event_data.get('tag_name', '')
        action = event_data.get('action', 'published')
        return f"{repo}:release:{tag_name}:{action}"
    
    elif event_type in ['star', 'fork']:
        # 使用操作者和时间戳
        sender = event_data.get('sender', {})
        sender_id = sender.get('id', '')
        timestamp = event_data.get('repository', {}).get('updated_at', '')
        return f"{repo}:{event_type}:{sender_id}:{timestamp}"
    
    return None