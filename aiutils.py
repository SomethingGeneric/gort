import os, json, subprocess, shutil
from time import sleep
import subprocess
import time

import openai

from github import GitHubApi


def shorten_url(url):
    # Placeholder for a URL shortening service
    # This should be replaced with actual logic to shorten the URL
    return "https://short.url/" + url.split('/')[-1]  # Simple demo shortening logic


def run_shell_command(command, cwd=None):
    try:
        result = subprocess.run(
            command, cwd=cwd, shell=True, capture_output=True, text=True
        )
        exit_code = result.returncode
        stdout = result.stdout.strip()
        return exit_code, stdout
    except Exception as e:
        return -1, str(e)


class llmUtils:
    def __init__(self, config):
        self.config = config
        self.git = GitHubApi(config)
        openai.api_key = config["ai_token"]
        self.assistant = openai.beta.assistants.retrieve(config["ai_assistant_id"])
        self.pending_tool_calls = 0  # Track pending tool requests
        self.tool_lock = False  # Lock to prevent submitting new tool calls
        self.main_prompt = """
You are a helpful junior developer named therattestman...
"""

    def create_messages_from_comments(self, comments, title, body=None):

        dialogue = [{"role": "user", "content": "Issue is titled: " + title}]
        if body:
            dialogue.append({"role": "user", "content": "Issue body: " + body})

        for comment in comments:
            usern = comment["user"]["login"] if "user" in comment else "mystery"
            role = "user" if usern != "therattestman" else "assistant"
            body = comment["body"]

            message = {"role": role, "content": body}
            dialogue.append(message)
        return dialogue

    def process_tool_calls(self, tool_calls, repo_slug):
        outputs = []
        owner, repo = repo_slug.split("/")
        for thing in tool_calls:
            try:
                arguments_json = thing.function.arguments
                arguments_dict = json.loads(arguments_json)
                name = thing.function.name
                call_id = thing.id

                print(f"Processing tool call with ID: {call_id}, Name: {name}")

                if "shell" in name:
                    command = arguments_dict["command"]
                    print(f"Running shell command: {command}")
                    code, outp = run_shell_command(command, cwd=repo)
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": json.dumps({"exit_code": code, "stdout": outp}),
                        }
                    )
                elif "writefile" in name:
                    file_path = arguments_dict["path"]
                    content = arguments_dict["content"]
                    print(f"Writing to file: {file_path}")
                    with open(repo + "/" + file_path, "w") as f:
                        f.write(content)
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": f"Successfully wrote to file: {file_path}",
                        }
                    )
                elif "push" in name:
                    commit_msg = arguments_dict["message"]
                    print("Pushing changes to the repository")
                    code, outp = run_shell_command(f"git add . && git commit -m '{commit_msg}' && git push", cwd=repo)
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": json.dumps({"exit_code": code, "stdout": outp}),
                        }
                    )
                elif "pr" in name:
                    title = arguments_dict["title"]
                    body = arguments_dict["body"]
                    print("Creating a pull request")
                    res = self.git.create_pull_request(owner, repo, title, body, "therattestman:main", "main")
                    pr_url = res.get("url")
                    short_pr_url = shorten_url(pr_url)
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": short_pr_url,
                        }
                    )
                self.pending_tool_calls += 1
            except Exception as e:
                outputs.append(
                    {"tool_call_id": call_id, "output": f"An error occurred: {str(e)}"}
                )
            finally:
                self.pending_tool_calls -= 1

        return outputs

    def get_response(self, comments, title, body, repo_slug):
        # Implementation of response generation from comments
        pass
