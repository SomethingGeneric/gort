# stdlib
import os
import getpass
import time
import json

# pip
import toml
from flask import Flask, request, jsonify

# local
from git import GiteaApi
from aiutils import llmUtils

app = Flask(__name__)

# Configuration
if not os.path.exists("config.toml"):
    endpoint = input("Enter the Gitea endpoint: ")
    username = input("Enter your Gitea username: ")
    password = getpass.getpass("Enter your Gitea password: ")
    token = getpass.getpass("Enter your Gitea token: ")
    ai_token = getpass.getpass("Enter your OpenAI token: ")
    ai_assistant_id = input("Enter your OpenAI assistant ID: ")

    with open("config.toml", "w") as f:
        toml.dump(
            {
                "endpoint": endpoint,
                "username": username,
                "password": password,
                "token": token,
                "ai_token": ai_token,
                "ai_assistant_id": ai_assistant_id,
            },
            f,
        )

config = None
with open("config.toml") as f:
    config = toml.load(f)

mygit = GiteaApi(config)
aihelper = llmUtils(config)

ignored_users = config.get("ignored_users", [])

@app.route('/register', methods=['POST'])
def register_repo():
    data = request.json
    repo_owner = data.get('repo_owner')
    repo_name = data.get('repo_name')
    webhook_url = data.get('webhook_url')
    
    # Add webhook to the repository
    webhook_config = {
        "type": "gitea",
        "config": {
            "url": webhook_url,
            "content_type": "json"
        },
        "events": ["issue", "issue_comment", "pull_request"],
        "active": True
    }
    response = mygit.add_webhook(repo_owner, repo_name, webhook_config)
    
    return jsonify(response), 200

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    payload = request.json
    event = request.headers.get('X-Gitea-Event')
    
    if event == 'issues' or event == 'issue_comment':
        action = payload.get('action')
        issue = payload.get('issue')
        repository = payload.get('repository')
        
        user = repository['owner']['login']
        repo_name = repository['name']
        issue_number = issue['number']
        
        if action == 'opened' or action == 'created':
            # Fetch issue comments
            comments = mygit.get_issue_comments(user, repo_name, issue_number)
            
            if len(comments) != 0 and comments[-1]['user']['login'] == 'gort':
                print("I was the last commenter, skipping...")
                return jsonify({"status": "skipped"}), 200
            
            # Generate AI response
            ai_resp = aihelper.get_response(comments, issue['title'], issue['body'], f"{user}/{repo_name}")
            print("Got from AI:", ai_resp)
            
            # Post comment to the issue
            mygit.post_issue_comment(user, repo_name, issue_number, ai_resp)
            print("Posted response to issue", issue_number, "in", user, repo_name)
    
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=5000)

