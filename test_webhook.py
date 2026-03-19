import json
import time
import uuid
from datetime import datetime, timedelta
import requests


def test_push_event(webhook_url):
    event = {
        "ref": "refs/heads/main",
        "before": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8",
        "after": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2",
        "repository": {
            "full_name": "test/repo",
            "name": "repo",
            "owner": {"login": "testuser"}
        },
        "pusher": {"name": "testuser"},
        "sender": {"login": "testuser"},
        "compare": "https://github.com/test/repo/compare/a1b2c3...b2c3d4e5",
        "commits": [
            {
                "id": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2",
                "message": "测试提交1",
                "author": {"name": "testuser"},
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "id": "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4",
                "message": "测试提交2",
                "author": {"name": "testuser"},
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "head_commit": {
            "id": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2",
            "message": "测试提交1",
            "author": {"name": "testuser"}
        }
    }
    send_event(webhook_url, "push", event)


def test_issues_event(webhook_url):
    event = {
        "action": "opened",
        "issue": {
            "number": 42,
            "title": "测试Issue标题",
            "state": "open",
            "html_url": "https://github.com/test/repo/issues/42",
            "comments": 5,
            "comments_url": "https://api.github.com/repos/test/repo/issues/42/comments",
            "labels": [
                {"name": "bug", "color": "d73a4a"},
                {"name": "enhancement", "color": "a2eeef"}
            ]
        },
        "repository": {
            "full_name": "test/repo",
            "name": "repo"
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "issues", event)


def test_pr_event(webhook_url):
    event = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "测试PR标题",
            "state": "open",
            "html_url": "https://github.com/test/repo/pull/123",
            "comments": 3,
            "review_comments": 2,
            "comments_url": "https://api.github.com/repos/test/repo/pulls/123/comments",
            "head": {
                "ref": "feature-branch",
                "repo": {"full_name": "test/repo"}
            },
            "base": {
                "ref": "main",
                "repo": {"full_name": "test/repo"}
            }
        },
        "repository": {
            "full_name": "test/repo",
            "name": "repo"
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "pull_request", event)


def test_release_event(webhook_url):
    event = {
        "action": "published",
        "release": {
            "tag_name": "v1.0.0",
            "name": "首个版本",
            "body": "这是第一个版本的发布说明\n\n- 新功能1\n- 新功能2",
            "html_url": "https://github.com/test/repo/releases/tag/v1.0.0",
            "assets": [
                {
                    "name": "app-v1.0.0.zip",
                    "size": 1024 * 1024 * 10,
                    "browser_download_url": "https://github.com/test/repo/releases/download/v1.0.0/app-v1.0.0.zip"
                },
                {
                    "name": "source-v1.0.0.tar.gz",
                    "size": 1024 * 512,
                    "browser_download_url": "https://github.com/test/repo/releases/download/v1.0.0/source-v1.0.0.tar.gz"
                }
            ]
        },
        "repository": {
            "full_name": "test/repo",
            "name": "repo"
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "release", event)


def test_star_event(webhook_url):
    event = {
        "starred_at": datetime.utcnow().isoformat(),
        "repository": {
            "full_name": "test/repo",
            "name": "repo",
            "stargazers_count": 42
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "star", event)


def test_fork_event(webhook_url):
    event = {
        "forkee": {
            "full_name": "testuser/repo-fork",
            "html_url": "https://github.com/testuser/repo-fork"
        },
        "repository": {
            "full_name": "test/repo",
            "name": "repo"
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "fork", event)


def test_workflow_event(webhook_url):
    event = {
        "action": "completed",
        "workflow_run": {
            "id": 123456789,
            "name": "CI",
            "run_number": 42,
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8",
            "html_url": "https://github.com/test/repo/actions/runs/123456789",
            "logs_url": "https://github.com/test/repo/actions/runs/123456789/logs",
            "created_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "head_commit": {
                "id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8",
                "message": "测试提交",
                "author": {"name": "testuser"}
            },
            "artifacts": [
                {
                    "name": "build-output.zip",
                    "size_in_bytes": 1024 * 1024 * 20,
                    "archive_download_url": "https://github.com/test/repo/actions/runs/123456789/artifacts/123456"
                },
                {
                    "name": "test-results.zip",
                    "size_in_bytes": 1024 * 500,
                    "archive_download_url": "https://github.com/test/repo/actions/runs/123456789/artifacts/123457"
                }
            ]
        },
        "repository": {
            "full_name": "test/repo",
            "name": "repo"
        },
        "sender": {"login": "testuser"}
    }
    send_event(webhook_url, "workflow_run", event)


def send_event(webhook_url, event_type, event_data):
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": event_type,
        "X-GitHub-Delivery": str(uuid.uuid4()),
    }
    
    print(f"\n{'='*50}")
    print(f"发送事件: {event_type}")
    print(f"{'='*50}")
    print(f"\n请求数据:")
    print(json.dumps(event_data, indent=2, ensure_ascii=False))
    print(f"\n发送到: {webhook_url}")
    
    try:
        response = requests.post(
            webhook_url,
            json=event_data,
            headers=headers,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ 发送成功！")
        else:
            print(f"\n❌ 发送失败，状态码: {response.status_code}")
    
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败，请检查URL是否正确")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")


def main():
    print("\n" + "="*50)
    print("GitHub Webhook 测试工具")
    print("="*50)
    
    webhook_url = input("\n请输入 Webhook URL: ").strip()
    if not webhook_url:
        print("URL不能为空！")
        return
    
    while True:
        print("\n" + "-"*50)
        print("请选择要测试的事件类型:")
        print("1. Push 事件")
        print("2. Issues 事件")
        print("3. Pull Request 事件")
        print("4. Release 事件")
        print("5. Star 事件")
        print("6. Fork 事件")
        print("7. Workflow 事件")
        print("0. 退出")
        print("-"*50)
        
        choice = input("\n请输入选项 (0-7): ").strip()
        
        if choice == "0":
            print("\n退出测试工具")
            break
        elif choice == "1":
            test_push_event(webhook_url)
        elif choice == "2":
            test_issues_event(webhook_url)
        elif choice == "3":
            test_pr_event(webhook_url)
        elif choice == "4":
            test_release_event(webhook_url)
        elif choice == "5":
            test_star_event(webhook_url)
        elif choice == "6":
            test_fork_event(webhook_url)
        elif choice == "7":
            test_workflow_event(webhook_url)
        else:
            print("\n无效选项，请重新选择")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    main()