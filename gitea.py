# pip
import requests


class GiteaApi:
    def __init__(self, config):
        self.token = config["gitea_token"]
        self.username = config["gitea_username"]
        self.password = config["gitea_password"]
        self.url = config["gitea_endpoint"]
        self.endpoint = self.url
        self.headers = {
            'Authorization': f'token {self.token}',
            'Content-Type': 'application/json'
        }

    def add_webhook(self, owner, repo, config):
        url = f"{self.endpoint}/repos/{owner}/{repo}/hooks"
        response = requests.post(url, headers=self.headers, data=json.dumps(config))
        return response.json()

    def get_users(self):
        """
        Retrieves a list of usernames for all users from the API.

        Returns:
            list: A list of usernames.
        """
        response = requests.get(
            f"{self.url}/api/v1/admin/users",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            stuff = response.json()
            usernames = []
            for user in stuff:
                usernames.append(user["username"])
            return usernames
        except:
            return [response.text]

    def get_user_orgs(self, username):
        """
        Retrieves the organizations that a user belongs to.

        Args:
            username (str): The username of the user.

        Returns:
            list: A list of organization usernames.

        Raises:
            Exception: If there is an error in the API response.
        """
        response = requests.get(
            f"{self.url}/api/v1/users/{username}/orgs",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            stuff = response.json()
            orgs = []
            for org in stuff:
                orgs.append(org["username"])
            return orgs
        except:
            return [response.text]

    def get_all_names(self):
        """
        Retrieves all names from users and organizations.

        Returns:
            list: A list of names from users and organizations.
        """
        users = self.get_users()
        orgs = []
        for user in users:
            for uorg in self.get_user_orgs(user):
                if uorg not in orgs:
                    orgs.append(uorg)
        return users + orgs

    def get_user_repos(self, username):
        """
        Retrieves the repositories of a given user.

        Args:
            username (str): The username of the user.

        Returns:
            dict or str: A dictionary containing the JSON response if successful, or the response text if an error occurred.
        """
        response = requests.get(
            f"{self.url}/api/v1/users/{username}/repos",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return response.text

    def get_prs(self, repo):
        """
        Get a list of pull requests for a given repository.

        Args:
            repo (str): The name of the repository.

        Returns:
            list: A list of pull requests in JSON format, or the response text if an error occurs.
        """
        response = requests.get(
            f"{self.url}/api/v1/repos/{repo}/pulls",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return response.text

    def get_issues(self, owner, repo):
        """
        Retrieves the issues for a given repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.

        Returns:
            dict or str: A dictionary containing the parsed JSON response if successful,
                         otherwise the raw response text.
        """
        response = requests.get(
            f"{self.url}/api/v1/repos/{owner}/{repo}/issues",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return response.text

    def get_issue(self, owner, repo, issuen):
        """
        Retrieves a specific issue from a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issuen (int): The issue number.

        Returns:
            dict or str: The JSON response containing the issue if successful, or the error message if unsuccessful.
        """
        response = requests.get(
            f"{self.url}/api/v1/repos/{owner}/{repo}/issues/{issuen}",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def get_issue_comments(self, owner, repo, issuen):
        """
        Retrieves the comments for a specific issue in a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issuen (int): The issue number.

        Returns:
            dict or str: The JSON response containing the comments if successful, or the error message if unsuccessful.
        """
        response = requests.get(
            f"{self.url}/api/v1/repos/{owner}/{repo}/issues/{issuen}/comments",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def post_issue_comment(self, owner, repo, issuen, comment):
        """
        Posts a comment to a specific issue in a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issuen (int): The issue number.
            comment (str): The comment to post.

        Returns:
            str: The response text.
        """

        response = requests.post(
            f"{self.url}/api/v1/repos/{owner}/{repo}/issues/{issuen}/comments",
            headers={"Authorization": f"token {self.token}"},
            json={"body": comment},
        )

        return response.json()

    def get_repo(self, owner, repo):
        """
        Retrieves a specific repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.

        Returns:
            dict or str: The JSON response containing the repository if successful, or the error message if unsuccessful.
        """
        response = requests.get(
            f"{self.url}/api/v1/repos/{owner}/{repo}",
            headers={"Authorization": f"token {self.token}"},
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def fork_repo(self, owner, repo):
        """
        Forks a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.

        Returns:
            dict or str: The JSON response containing the repository if successful, or the error message if unsuccessful.
        """
        response = requests.post(
            f"{self.url}/api/v1/repos/{owner}/{repo}/forks",
            headers={"Authorization": f"token {self.token}"},
            json={"name": repo},
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def create_pull_request(
        self, owner, repo, title, body, source_branch, target_branch
    ):
        """
        Creates a pull request from a user's repository to the source repository.

        Args:
            owner (str): The owner of the user's repository.
            repo (str): The name of the user's repository.
            title (str): The title of the pull request.
            body (str): The body of the pull request.
            source_branch (str): The source branch of the pull request.
            target_branch (str): The target branch of the pull request.

        Returns:
            dict or str: The JSON response containing the pull request if successful, or the error message if unsuccessful.
        """
        response = requests.post(
            f"{self.url}/api/v1/repos/{owner}/{repo}/pulls",
            headers={"Authorization": f"token {self.token}"},
            json={
                "title": title,
                "body": body,
                "head": source_branch,
                "base": target_branch,
            },
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}


if __name__ == "__main__":
    import toml

    g = GiteaApi(toml.load("config.toml"))

    if "couldn't be found" in g.get_repo("gort", "website")["message"]:
        print(g.fork_repo("matt", "website"))
