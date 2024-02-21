import os, json, subprocess, shutil
from time import sleep
import subprocess

import openai

from git import GiteaApi


def run_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
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

        self.git = GiteaApi(config)

        self.main_prompt = """
You are a helpful junior developer named Gort. You are working on a project with a coworker.
Try to help them as best as you can.

Feel free to ask the user for more information if you need it.

DO NOT RESPOND WITH ONLY JSON DATA.
YOU ARE NOT A JSON API.

You *can* use markdown formatting if you want to.

Do not respond ONLY with code. Explain what the code does and why it is needed.

Explain what you want the user to do, rather than just telling them what to do.

If you use a function, like the shell, ALWAYS show the output of the function to the user.

"""

    def create_messages_from_comments(self, comments, title, body):

        dialogue = [{"role": "user", "content": "Issue is titled: " + title}]
        dialogue.append({"role": "user", "content": "Issue body: " + body})

        for comment in comments:
            usern = comment["user"]["login"] if "user" in comment else "mystery"
            role = "user" if usern != "gort" else "assistant"
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
        try:
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant.id,
            )

            finished = False

            while not finished:

                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id, run_id=run.id
                )

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
                        arguments_json = thing.function.arguments
                        arguments_dict = json.loads(arguments_json)

                        name = thing.function.name
                        call_id = thing.id

                        print(f"Doing action {str(name)} for call: {str(call_id)}")

                        outputs = []

                        if "shell" in name:
                            # prep work
                            owner = repo_slug.split("/")[0].strip()
                            repo = repo_slug.split("/")[1].strip()

                            if (
                                "couldn't be found"
                                in self.git.get_repo("gort", repo)["message"]
                            ):
                                # need to fork
                                print(self.git.fork_repo(owner, repo))

                            os.system(
                                f"git clone {self.config['endpoint']}/gort/{repo}.git"
                            )

                            # required
                            command = f"cd {repo} && " + arguments_dict["command"]

                            code, outp = run_shell_command(command)

                            res = {
                                "exit_code": code,
                                "stdout": outp,
                            }

                            me = {
                                "tool_call_id": call_id,
                                "output": str(res),
                            }

                            outputs.append(me)

                            shutil.rmtree(repo)

                        else:
                            print("Unknown action name: " + str(name))

                        run = openai.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=outputs,
                        )

                sleep(5)  # TODO: some kind of exponential backoff

        except Exception as e:
            return "BIG BAD ERROR: " + str(
                e
            )  # TODO: figure out why some of the OpenAI functions (I think?) only bubble up as just 'message' instead of a good error message.
