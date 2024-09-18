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
        openai.api_key = config["ai_token"]

        self.assistant = openai.beta.assistants.retrieve(config["ai_assistant_id"])

        self.git = GitHubApi(config)

        self.main_prompt = """
You are a helpful junior developer named therattestman. You are working on a project with a coworker.
Try to help them as best as you can.

Feel free to ask the user for more information if you need it.

DO NOT RESPOND WITH ONLY JSON DATA.
YOU ARE NOT A JSON API.

You *can* use markdown formatting if you want to.

Do not respond ONLY with code. Explain what the code does and why it is needed.

If you use the shell function, ALWAYS show the output of the function to the user.

Use the shell to access referenced files. Do not ask the user for the content of a file, you already have it.

Consider the state of the repository when you are making changes.

Once you are done reading and/or writing files, if you believe you have made changes that should persist in the repository, use the commit function to commit the changes to the remote repository.

Keep in mind that multi-line formatting in the shell may not work.

If you need to modify a file, you should use the writefile function to write the file.

You can then inform the user of the changes you made and the commit message you used, and that the changes are now in the remote repository.

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

    def get_response(self, comments, title, body, repo_slug):
        thread = (
            openai.beta.threads.create()
        )  # TODO: save a thread for each issue, and load it if it exists
        msg = [{"role": "system", "content": self.main_prompt}]
        msg += self.create_messages_from_comments(comments, title, body)

        for item in msg:
            openai.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=item["content"]
            )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
        )

        # prep work
        owner = repo_slug.split("/")[0].strip()
        repo = repo_slug.split("/")[1].strip()

        finished = False

        while not finished:
            # Log run status
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status}")

            if run.status == "completed":
                finished = True
                omessages = openai.beta.threads.messages.list(thread_id=thread.id)
                omessage = omessages.data[0]
                raw_resp = omessage.content[0].text.value
                shutil.rmtree(repo)  # clean up
                return raw_resp

            elif run.status == "failed":
                finished = True
                return "The AI failed to generate a response."

            elif run.status == "requires_action":
                action = run.required_action
                tool_calls = action.submit_tool_outputs.tool_calls

                print(f"Number of tool calls received: {len(tool_calls)}")

                for thing in tool_calls:
                    try:
                        arguments_json = thing.function.arguments
                        arguments_dict = json.loads(arguments_json)

                        name = thing.function.name
                        call_id = thing.id

                        print(f"Processing tool call with ID: {call_id}, Name: {name}")

                        if not os.path.exists(repo):
                            repo_check = self.git.get_repo("therattestman", repo)
                            if (
                                "message" in repo_check
                                and "Not Found" in repo_check["message"]
                            ):
                                # need to fork
                                print("Forking repo")
                                self.git.fork_repo(owner, repo)

                            print(f"Cloning repo: {repo}")
                            print(
                                f"Target URL: git@github.com:therattestman/{repo}.git"
                            )
                            os.system(
                                f"git clone git@github.com:therattestman/{repo}.git"
                            )
                        else:
                            os.system(f"cd {repo} && git pull")

                        outputs = []

                        if "shell" in name:
                            command = arguments_dict["command"]
                            print(f"Running shell command: {command}")

                            try:
                                code, outp = run_shell_command(command, cwd=repo)
                                res = {
                                    "exit_code": code,
                                    "stdout": outp,
                                }
                            except Exception as e:
                                res = {
                                    "exit_code": -1,
                                    "stdout": f"Error running shell command: {str(e)}",
                                }

                            outputs.append(
                                {
                                    "tool_call_id": call_id,
                                    "output": json.dumps(res),
                                }
                            )
                            print(f"Shell command exit code: {res['exit_code']}")

                        elif "writefile" in name:
                            try:
                                filename = arguments_dict["path"]
                                content = arguments_dict["content"]
                                with open(f"{repo}/{filename}", "w") as f:
                                    f.write(content)
                                res = "File written successfully."
                            except Exception as e:
                                res = f"Error writing file: {str(e)}"

                            outputs.append(
                                {
                                    "tool_call_id": call_id,
                                    "output": res,
                                }
                            )
                            print(f"Write file result: {res}")

                        elif "push" in name:
                            print("Running git push")
                            try:
                                command = "git status --porcelain"
                                code, outp = run_shell_command(command, cwd=repo)
                                if outp:
                                    msg = arguments_dict["message"]
                                    commit_cmd = f"git add . && git commit -m '{msg}'"
                                    commit_code, commit_outp = run_shell_command(
                                        commit_cmd, cwd=repo
                                    )

                                    push_cmd = "git push origin"
                                    push_code, push_outp = run_shell_command(
                                        push_cmd, cwd=repo
                                    )

                                    res = {
                                        "commit_code": commit_code,
                                        "commit_stdout": commit_outp,
                                        "push_code": push_code,
                                        "push_stdout": push_outp,
                                    }
                                else:
                                    res = "No changes to commit and push."

                            except Exception as push_exception:
                                res = f"Error pushing changes: {str(push_exception)}"

                            outputs.append(
                                {
                                    "tool_call_id": call_id,
                                    "output": json.dumps(res),
                                }
                            )
                            print(f"Push result: {res}")

                        elif "pr" in name:
                            base_branch = "main"
                            head_branch = "therattestman:main"
                            title = arguments_dict["title"]
                            body = arguments_dict["body"]
                            pr = self.git.create_pull_request(
                                owner, repo, base_branch, head_branch, title, body
                            )
                            res = {"pr_raw": str(pr)}

                            outputs.append(
                                {
                                    "tool_call_id": call_id,
                                    "output": json.dumps(res),
                                }
                            )
                            print(f"Pull request result: {res}")

                        else:
                            print(f"Unknown action name: {name}")
                            res = f"Unknown action name: {name}"
                            outputs.append(
                                {
                                    "tool_call_id": call_id,
                                    "output": res,
                                }
                            )

                        # Log and submit tool outputs
                        print(f"Submitting tool outputs for call ID: {call_id}")
                        print(f"Outputs: {json.dumps(outputs, indent=2)}")

                    except Exception as e:
                        print(f"An error occurred while processing tool call: {str(e)}")
                        outputs.append(
                            {
                                "tool_call_id": call_id,
                                "output": f"An error occurred: {str(e)}",
                            }
                        )
                try:
                    run = openai.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=outputs,
                    )
                except Exception as e:
                    print(f"Error submitting tool outputs: {str(e)}")

            time.sleep(5)  # TODO: implement exponential backoff
