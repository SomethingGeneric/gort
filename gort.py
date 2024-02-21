# stdlib
import os, getpass, time

# pip
import toml

# local
from git import GiteaApi
from aiutils import llmUtils

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

ignored_users = []
if "ignored_users" in config:
    ignored_users = config["ignored_users"]

running = True

while running:

    names = mygit.get_all_names()

    for user in names:
        repos = mygit.get_user_repos(user)
        for repo in repos:
            #print("Checking", user, repo['name'])
            issues = mygit.get_issues(user, repo["name"])

            for issue in issues:
                if (
                    issue["user"]["login"] not in ignored_users
                    and issue["state"] == "open"
                    and issue["title"].startswith("Gort")
                ):
                    n = issue["number"]
                    print("Found issue", n, "in", user, repo["name"])

                    print("Generating response...")

                    comments = mygit.get_issue_comments(user, repo["name"], n)

                    if len(comments) != 0:
                        if comments[-1]["user"]["login"] == "gort":
                            print("I was the last commenter, skipping...")
                            continue

                    ai_resp = aihelper.get_response(
                        comments, issue["title"], issue["body"]
                    )

                    mygit.post_issue_comment(user, repo["name"], n, ai_resp)

                    print("Posted response to issue", n, "in", user, repo["name"])

    print("Sleeping for 60 seconds...")
    time.sleep(60)
    print("Restarting loop")
