                elif "pr" in name:
                    title = arguments_dict["title"]
                    body = arguments_dict["body"]
                    print("Creating a pull request")
                    res = self.git.create_pull_request(owner, repo, title, body, "therattestman:main", "main")
                    # Assuming res contains a field 'url' that gives the full URL
                    pr_url = res.get("url")  # Replace with the actual field accessing method
                    # Convert to a short URL (example function)
                    short_pr_url = self.shorten_url(pr_url)
                    outputs.append(
                        {
                            "tool_call_id": call_id,
                            "output": short_pr_url,
                        }
                    )
