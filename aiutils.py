import os, json, subprocess, shutil
from time import sleep
import subprocess

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

            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

            if run.status == "completed":
                finished = True
                omessages = openai.beta.threads.messages.list(thread_id=thread.id)
                omessage = omessages.data[0]
                raw_resp = omessage.content[0].text.value
                return raw_resp
            elif run.status == "failed":
                finished = True
                return "The AI failed to generate a response."
            elif run.status == "requires_action":
                action = run.required_action
                for thing in action.submit_tool_outputs.tool_calls:

                    try:

                        arguments_json = thing.function.arguments
                        arguments_dict = json.loads(arguments_json)

                        name = thing.function.name
                        call_id = thing.id

                        if not os.path.exists(repo):
                            if (
                                "message" in self.git.get_repo("therattestman", repo).keys()
                                and "couldn't be found"
                                in self.git.get_repo("therattestman", repo)["message"]
                            ):
                                # need to fork
                                print(self.git.fork_repo(owner, repo))

                            os.system(
                                f"git clone git@github.com:therattestman/{repo}.git"
                            )
                        else:
                            os.system(f"cd {repo} && git pull")

                        print(f"Doing action {str(name)} for call: {str(call_id)}")

                        outputs = []

                        if "shell" in name:

                            # required
                            command = arguments_dict["command"]

                            print("Running command: " + command)

                            try:
                                code, outp = run_shell_command(command, cwd=repo)

                                res = {
                                    "exit_code": code,
                                    "stdout": outp,
                                }

                                print("No exception occurred, exit code " + str(code))
                            except Exception as e:
                                res = {
                                    "exit_code": -1,
                                    "stdout": "The backend reports error: " + str(e),
                                }
                                print("Exception occurred, exit code " + str(code))

                            me = {
                                "tool_call_id": call_id,
                                "output": str(res),
                            }

                            outputs.append(me)

                            print("Shell stats done")

                        elif "gitlog" in name:
                            command = "git --no-pager log"
                            code, outp = run_shell_command(command, cwd=repo)

                            res = {
                                "exit_code": code,
                                "stdout": outp,
                            }

                            me = {
                                "tool_call_id": call_id,
                                "output": str(res),
                            }

                            outputs.append(me)
                        elif "writefile" in name:
                            try:
                                filename = arguments_dict["path"]
                                content = arguments_dict["content"]
                                with open(f"{repo}/{filename}", "w") as f:
                                    f.write(content)
                                me = {
                                    "tool_call_id": call_id,
                                    "output": "File written successfully.",
                                }
                            except Exception as e:
                                me = {
                                    "tool_call_id": call_id,
                                    "output": "Error writing file: " + str(e),
                                }
                            outputs.append(me)
                        elif "commit" in name or "push" in name:
                            try:

                                command = "git status --porcelain"
                                code, outp = run_shell_command(command, cwd=repo)
                                if outp:  # If there is output, changes are detected
                                    # Git commit changes
                                    msg = arguments_dict["message"]
                                    commit_cmd = (
                                        f"&& git add . && git commit -m '{msg}'"
                                    )
                                    commit_code, commit_outp = run_shell_command(
                                        commit_cmd, cwd=repo
                                    )
                                    print(f"Commit operation output: {commit_outp}")

                                    # Git push changes
                                    push_cmd = "git push origin"
                                    push_code, push_outp = run_shell_command(
                                        push_cmd, cwd=repo
                                    )
                                    print(f"Push operation output: {push_outp}")

                                    res = {
                                        "commit_code": commit_code,
                                        "commit_stdout": commit_outp,
                                        "push_code": push_code,
                                        "push_stdout": push_outp,
                                    }
                                else:
                                    res = {
                                        "push_stdout": "No changes detected, no commit or push was made."
                                    }

                                me = {
                                    "tool_call_id": call_id,
                                    "output": str(res),
                                }

                                outputs.append(me)

                            except Exception as push_exception:
                                print(
                                    f"An error occurred while pushing changes: {push_exception}"
                                )

                                me = {
                                    "tool_call_id": call_id,
                                    "output": "Error occured: " + str(push_exception),
                                }

                                outputs.append(me)

                            shutil.rmtree(repo)

                        else:
                            print("Unknown action name: " + str(name))
                            me = {
                                "tool_call_id": call_id,
                                "output": "Unknown action name: " + str(name),
                            }
                            outputs.append(me)

                        run = openai.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=outputs,
                        )

                    except Exception as e:
                        print("An error occurred: " + str(e))
                        return "An error occurred: " + str(e)

            sleep(5)  # TODO: some kind of exponential backoff
