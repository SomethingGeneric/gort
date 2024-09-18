import requests
import json
import toml

# pip


class GitHubApi:
    def __init__(self, config):
        self.token = config["github_pat"]
        self.headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    def add_webhook(self, owner, repo, config):
        url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
        response = requests.post(url, headers=self.headers, data=json.dumps(config))
        return response.json()

    def get_users(self):
        """
        Retrieves a list of usernames for all users from the API.

        Returns:
            list: A list of usernames.
        """
        return ["SomethingGeneric"]

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
            f"https://api.github.com/users/{username}/orgs",
            headers=self.headers,
        )
        try:
            stuff = response.json()
            orgs = []
            for org in stuff:
                orgs.append(org["login"])
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
            f"https://api.github.com/users/{username}/repos",
            headers=self.headers,
        )
        try:
            return response.json()
        except:
            return response.text

    def get_prs(self, owner, repo):
        """
        Get a list of pull requests for a given repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.

        Returns:
            list: A list of pull requests in JSON format, or the response text if an error occurs.
        """
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=self.headers,
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
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers=self.headers,
        )
        try:
            return response.json()
        except:
            return response.text

    def get_issue(self, owner, repo, issue_number):
        """
        Retrieves a specific issue from a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issue_number (int): The issue number.

        Returns:
            dict or str: The JSON response containing the issue if successful, or the error message if unsuccessful.
        """
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            headers=self.headers,
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def get_issue_comments(self, owner, repo, issue_number):
        """
        Retrieves the comments for a specific issue in a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issue_number (int): The issue number.

        Returns:
            dict or str: The JSON response containing the comments if successful, or the error message if unsuccessful.
        """
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
            headers=self.headers,
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def post_issue_comment(self, owner, repo, issue_number, comment):
        """
        Posts a comment to a specific issue in a repository.

        Args:
            owner (str): The owner of the repository.
            repo (str): The name of the repository.
            issue_number (int): The issue number.
            comment (str): The comment to post.

        Returns:
            str: The response text.
        """

        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
            headers=self.headers,
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
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=self.headers,
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
            f"https://api.github.com/repos/{owner}/{repo}/forks",
            headers=self.headers,
            json={"name": repo},
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}

    def create_pull_request(self, owner, repo, title, body, head_branch, base_branch):
        """
        Creates a pull request from a user's repository to the source repository.

        Args:
            owner (str): The owner of the user's repository.
            repo (str): The name of the user's repository.
            title (str): The title of the pull request.
            body (str): The body of the pull request.
            head_branch (str): The source branch of the pull request.
            base_branch (str): The target branch of the pull request.

        Returns:
            dict or str: The JSON response containing the pull request if successful, or the error message if unsuccessful.
        """
        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=self.headers,
            json={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
            },
        )
        try:
            return response.json()
        except:
            return {"msg": response.text}


if __name__ == "__main__":

    g = GitHubApi(toml.load("config.toml"))

    # print(g.get_repo('SomethingGeneric', 'gort'))
    print(g.get_repo("therattestman", "gort"))
