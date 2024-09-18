import os, json, subprocess, shutil
from time import sleep
import subprocess
import time

import openai

from github import GitHubApi


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
        self.github = GitHubApi(config)
        openai.api_key = config["ai_token"]
        self.assistant = openai.beta.assistants.retrieve(config["ai_assistant_id"])
        self.pending_tool_calls = 0  # Track pending tool requests
        self.tool_lock = False  # Lock to prevent submitting new tool calls
        self.main_prompt = """
You are a helpful junior developer named therattestman. You are working on a project with a coworker.

DO NOT RESPOND WITH ONLY JSON DATA.
YOU ARE NOT A JSON API.

You *can* use markdown formatting if you want to.

Do not respond ONLY with code. Explain what the code does and why it is needed.

If you use the shell function, ALWAYS show the output of the function to the user.

Use the shell to access referenced files. Do not ask the user for the content of a file, you already have it.

Consider the state of the repository when you are making changes.

Keep in mind that multi-line formatting in the shell may not work.

If you need to modify a file, you should use the writefile function to write the file.

You are automatically put in a working directory with the relevant repository files checked out. (Cloned with git).
You will also be operating on a fork of the repository, not the original, so that you can create pull requests with your changes.

Assuming that you don't need to ask for clarification, you should follow this process:
1. Use shell commands to find relevant files and read them
2. Use shell commands and/or writefile to make changes
3. Use the push command to commit and push the changes to your fork of the repository
4. Use pr to create a pull request with the changes to the user's repository

You can repeat steps 1 and 2 as many times as needed before committing/pushing and opening a pull request.

Do NOT run git commands directly. Use the provided functions instead.

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

    def process_tool_calls(self, tool_calls, owner, repo):
        outputs = []
        for thing in tool_calls:
            try:
                arguments_json = thing.function.arguments
                arguments_dict = json.loads(arguments_json)
                name = thing.function.name
                call_id = thing.id

                print(f"Processing tool call with ID: {call_id}, Name: {name}")

                # Simulate tool execution based on the tool name (e.g., shell, writefile)
                if "shell" in name:
                    command = arguments_dict["command"]
                    print(f"Running shell command: {command}")
                    code, outp = run_shell_command(command)
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
                    with open(file_path, "w") as f:
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
                    code, outp = run_shell_command(f"git add . && git commit -m '{commit_msg}' && git push")
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
                    res = self.github.create_pull_request(owner, repo, title, body, "therattestman:main", "main")
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": str(res),
                        }
                    )
                # Track number of pending tool calls
                self.pending_tool_calls += 1

            except Exception as e:
                outputs.append(
                    {"tool_call_id": call_id, "output": f"An error occurred: {str(e)}"}
                )
            finally:
                # Decrease the pending tool count when done
                self.pending_tool_calls -= 1

        return outputs

    def get_response(self, comments, title, body, repo_slug):
        thread = openai.beta.threads.create()
        msg = [{"role": "system", "content": self.main_prompt}]
        msg += self.create_messages_from_comments(comments, title, body)
        for item in msg:
            openai.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=item["content"]
            )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=self.assistant.id
        )
        finished = False

        while not finished:
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

            if run.status == "requires_action":
                action = run.required_action
                tool_calls = action.submit_tool_outputs.tool_calls

                if len(tool_calls) > 0:
                    if not self.tool_lock:  # Only process if lock is released
                        self.tool_lock = True  # Lock while processing tool calls
                        outputs = self.process_tool_calls(tool_calls, owner, repo_slug)

                        # Submit tool outputs
                        openai.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread.id, run_id=run.id, tool_outputs=outputs
                        )

                        # Unlock when all pending tool calls are done
                        if self.pending_tool_calls == 0:
                            self.tool_lock = False

            elif run.status == "completed":
                finished = True
                return run.messages[-1].content

            elif run.status == "failed":
                finished = True
                return "I'm sorry, I encountered an error."

            time.sleep(1)  # Exponential backoff could also be applied here
