import hashlib
import hmac
import uuid
from datetime import datetime


def generate_uuid_short(length=4):
    return uuid.uuid4().hex[:length]


def verify_signature(payload, signature, secret):
    if not signature or not secret:
        return False
    
    if not signature.startswith('sha256='):
        return False
    
    hash_algorithm, github_signature = signature.split('=', 1)
    mac = hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    return hmac.compare_digest(expected_signature, github_signature)


def format_timestamp(timestamp):
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def get_event_key(repo, event_type, event_data):
    if event_type == 'push':
        head_commit = event_data.get('head_commit', {})
        commit_id = head_commit.get('id', event_data.get('after', ''))
        return f"{repo}:push:{commit_id}"
    
    elif event_type in ['issues', 'pull_request']:
        number = event_data.get('number', '')
        action = event_data.get('action', '')
        return f"{repo}:{event_type}:{number}:{action}"
    
    elif event_type == 'release':
        tag_name = event_data.get('tag_name', '')
        action = event_data.get('action', 'published')
        return f"{repo}:release:{tag_name}:{action}"
    
    elif event_type in ['star', 'fork']:
        sender = event_data.get('sender', {})
        sender_id = sender.get('id', '')
        timestamp = event_data.get('repository', {}).get('updated_at', '')
        return f"{repo}:{event_type}:{sender_id}:{timestamp}"
    
    elif event_type == 'workflow_run':
        workflow_run = event_data.get('workflow_run', {})
        run_id = workflow_run.get('id', '')
        action = event_data.get('action', '')
        return f"{repo}:workflow_run:{run_id}:{action}"
    
    return None