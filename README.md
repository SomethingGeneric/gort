# gort

Gort is an AI developer who will help you implement code features based on issue details

## Dev steps
1. Gitea/Forgejo api to:
    1. Scan all repos of every org and user (if set public)
    2. Find all issues on any repo that have a `Gort` tag or `Gort:` in title
    3. Fork, push, and open PR to origional repo that triggered action
2. OpenAI api to:
    1. Decide upon relevant files given issue details and repo details (language, packing system etc)
    2. Feed in relevant files and issue description
    3. Get out changes to files to use in git api calls