# stdlib
import os
import getpass
import time
import json

# pip
import toml
from flask import Flask, request, jsonify

# local
from gitea import GiteaApi
from github import GitHubApi
from aiutils import llmUtils

app = Flask(__name__)

# Configuration
if not os.path.exists("config.toml"):
    gitea_endpoint = input("Enter the Gitea endpoint: ")
    gitea_username = input("Enter your bot's Gitea username: ")
    gitea_password = getpass.getpass("Enter your bot's Gitea password: ")
    token = getpass.getpass("Enter your bot's Gitea token: ")

    ai_token = getpass.getpass("Enter your OpenAI token: ")
    ai_assistant_id = input("Enter your OpenAI assistant ID: ")

    github_username = input("Enter your bot's GitHub username: ")
    github_pat = getpass.getpass("Enter your bot's GitHub personal access token: ")

    with open("config.toml", "w") as f:
        toml.dump(
            {
                "gitea_endpoint": gitea_endpoint,
                "gitea_username": gitea_username,
                "gitea_password": gitea_password,
                "gitea_token": token,
                "ai_token": ai_token,
                "ai_assistant_id": ai_assistant_id,
                'github_username': github_username,
                'github_pat': github_pat,
            },
            f,
        )

config = None
with open("config.toml") as f:
    config = toml.load(f)

mygitea = GiteaApi(config)
mygithub = GitHubApi(config)
aihelper = llmUtils(config)

ignored_users = config.get("ignored_users", [])

@app.route('/gitea/register', methods=['POST'])
def gt_register_repo():
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
    response = mygitea.add_webhook(repo_owner, repo_name, webhook_config)
    
    return jsonify(response), 200

@app.route('/gitea/webhook', methods=['POST'])
def gt_handle_webhook():
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
            comments = mygitea.get_issue_comments(user, repo_name, issue_number)
            
            if len(comments) != 0 and comments[-1]['user']['login'] == 'gort':
                print("I was the last commenter, skipping...")
                return jsonify({"status": "skipped"}), 200
            
            # Generate AI response
            ai_resp = aihelper.get_response(comments, issue['title'], issue['body'], f"{user}/{repo_name}")
            print("Got from AI:", ai_resp)
            
            # Post comment to the issue
            mygitea.post_issue_comment(user, repo_name, issue_number, ai_resp)
            print("Posted response to issue", issue_number, "in", user, repo_name)
    
    return jsonify({"status": "success"}), 200

## END GITEA
## START GITHUB

@app.route('/github/register', methods=['POST'])
def gh_register_repo():
    data = request.json
    repo_owner = data.get('repo_owner')
    repo_name = data.get('repo_name')
    webhook_url = data.get('webhook_url')
    
    # Add webhook to the repository
    webhook_config = {
        "type": "github",  # Change the type to "github"
        "config": {
            "url": webhook_url,
            "content_type": "json"
        },
        "events": ["issue", "issue_comment", "pull_request"],
        "active": True
    }
    response = mygithub.add_webhook(repo_owner, repo_name, webhook_config)  # Use mygithub instead of mygit
    
    return jsonify(response), 200

@app.route('/github/webhook', methods=['POST'])
def gh_handle_webhook():
    payload = request.json
    event = request.headers.get('X-GitHub-Event')
    
    if event == 'issues' or event == 'issue_comment':
        action = payload.get('action')
        issue = payload.get('issue')
        repository = payload.get('repository')
        
        user = repository['owner']['login']
        repo_name = repository['name']
        issue_number = issue['number']
        
        if action == 'opened' or action == 'created':
            # Fetch issue comments
            comments = mygithub.get_issue_comments(user, repo_name, issue_number)
            
            if len(comments) != 0 and comments[-1]['user']['login'] == 'gort':
                print("I was the last commenter, skipping...")
                return jsonify({"status": "skipped"}), 200
            
            # Generate AI response
            ai_resp = aihelper.get_response(comments, issue['title'], issue['body'], f"{user}/{repo_name}")
            print("Got from AI:", ai_resp)
            
            # Post comment to the issue
            mygithub.post_issue_comment(user, repo_name, issue_number, ai_resp)
            print("Posted response to issue", issue_number, "in", user, repo_name)
    
    return jsonify({"status": "success"}), 200


if __name__ == '__main__':
    app.run(port=5001)

