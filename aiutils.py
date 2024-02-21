import requests
import openai


class llmUtils:
    def __init__(self, config):
        self.source = config['ai_source']
        self.token = config['ai_token'] if self.source == "openai" else None

        self.main_prompt = """
You are a helpful junior developer named Gort. You are working on a project with a coworker.
Try to help them as best as you can.

Feel free to ask the user for more information if you need it.

DO NOT RESPOND WITH ONLY JSON DATA.
YOU ARE NOT A JSON API.

You *can* use markdown formatting if you want to.

Do not respond ONLY with code. Explain what the code does and why it is needed.

"""

    def create_messages_from_comments(self, comments, title, body):

        #print(comments)

        dialogue = [{"role": "user", "content": "Issue is titled: " + title}]
        dialogue.append({"role": "user", "content": "Issue body: " + body})

        for comment in comments:
            usern = comment["user"]["login"] if "user" in comment else "mystery"
            role = "user" if usern != "gort" else "assistant"
            body = comment["body"]

            message = {"role": role, "content": body}
            dialogue.append(message)
        return dialogue

    def get_response(self, comments, title, body):
        

        msg = [{"role": "system", "content": self.main_prompt}]
        msg += self.create_messages_from_comments(comments, title, body)

        if self.source == "ollama":

            url = "http://127.0.0.1:11434/api/chat"
            data = {
                "model": "llama2-uncensored",
                "messages": msg,
                "stream": False,
                "format": "json",
            }
            response = requests.post(url, json=data)
            try:
                thresponse = response.json()['message']['content']
            except:
                thresponse = response.text

            return thresponse
        elif self.source == "openai":
            try:
                client = openai.OpenAI(api_key=self.token)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=msg,
                )

                thresponse = response.choices[0].message.content.strip()

                return thresponse
            except Exception as e:
                return str(e)
        else:
            return "Not implemented/valid"
