import hashlib
import hmac
import re
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


def _inline_md_to_html(text):
    if not text:
        return ""
    text = re.sub(r'`([^`]+)`', r'<code style="background: rgba(0,0,0,0.06); padding: 1px 4px; border-radius: 3px; font-size: 12px;">\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #1565c0; text-decoration: none;">\1</a>', text)
    return text


def markdown_to_html(md_text):
    if not md_text:
        return ""
    lines = md_text.split('\n')
    html_parts = []
    in_list = False
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code_block:
                html_parts.append('</code></pre>')
                in_code_block = False
            else:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                lang = stripped[3:].strip()
                html_parts.append(f'<pre><code{f" class={lang}" if lang else ""}>')
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(_inline_md_to_html(line))
            continue

        if re.match(r'^---+\s*$', stripped):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append('<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 8px 0;">')
            continue

        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            level = len(header_match.group(1))
            sizes = {1: '18px', 2: '16px', 3: '14px', 4: '13px', 5: '13px', 6: '12px'}
            size = sizes.get(level, '13px')
            content = _inline_md_to_html(header_match.group(2))
            html_parts.append(f'<div style="font-size: {size}; font-weight: bold; margin: 8px 0 4px;">{content}</div>')
            continue

        if stripped.startswith('>'):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            quote_content = re.sub(r'^>\s*', '', stripped)
            html_parts.append(f'<div style="border-left: 3px solid #1565c0; padding: 4px 8px; margin: 4px 0; color: #555; font-size: 13px;">{_inline_md_to_html(quote_content)}</div>')
            continue

        list_match = re.match(r'^(\s*)-\s+(.*)$', line)
        if list_match:
            indent = len(list_match.group(1))
            content = _inline_md_to_html(list_match.group(2))
            if not in_list:
                html_parts.append('<ul style="margin: 4px 0; padding-left: 20px;">')
                in_list = True
            margin = f"margin-left: {indent * 8}px; " if indent > 0 else ""
            html_parts.append(f'<li style="{margin}font-size: 13px; margin-bottom: 2px;">{content}</li>')
            continue

        if in_list:
            html_parts.append('</ul>')
            in_list = False

        if not stripped:
            html_parts.append('<div style="height: 6px;"></div>')
            continue

        html_parts.append(f'<div style="font-size: 13px; line-height: 1.6;">{_inline_md_to_html(stripped)}</div>')

    if in_list:
        html_parts.append('</ul>')
    if in_code_block:
        html_parts.append('</code></pre>')

    return '\n'.join(html_parts)