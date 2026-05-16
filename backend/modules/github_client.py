import httpx
import base64
from loguru import logger


GITHUB_API = "https://api.github.com"
HEADERS_BASE = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


class GithubClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}"}

    async def get_user(self) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/user", headers=self.headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            return {
                "login": data["login"],
                "name": data.get("name"),
                "avatar_url": data.get("avatar_url"),
                "public_repos": data.get("public_repos", 0),
                "followers": data.get("followers", 0),
            }

    async def list_repos(self, per_page: int = 100) -> list[dict]:
        repos = []
        page = 1
        async with httpx.AsyncClient() as client:
            while True:
                r = await client.get(
                    f"{GITHUB_API}/user/repos",
                    headers=self.headers,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "pushed",
                        "direction": "desc",
                        "affiliation": "owner",
                    },
                    timeout=30,
                )
                r.raise_for_status()
                batch = r.json()
                if not batch:
                    break
                repos.extend(batch)
                if len(batch) < per_page:
                    break
                page += 1
        logger.info(f"[GithubClient] Fetched {len(repos)} repos")
        return repos

    async def get_readme(self, owner: str, repo: str) -> str | None:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/readme",
                headers=self.headers,
                timeout=15,
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            content = data.get("content", "")
            encoding = data.get("encoding", "base64")
            if encoding == "base64" and content:
                try:
                    return base64.b64decode(content).decode("utf-8", errors="replace")
                except Exception:
                    return None
            return content or None

    async def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
                headers=self.headers,
                params={"recursive": "1"},
                timeout=20,
            )
            if r.status_code == 404:
                if branch == "main":
                    return await self.get_repo_tree(owner, repo, "master")
                return []
            r.raise_for_status()
            data = r.json()
            return data.get("tree", [])

    async def get_languages(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/languages",
                headers=self.headers,
                timeout=15,
            )
            if r.status_code != 200:
                return {}
            return r.json()

    async def get_repo_details(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}",
                headers=self.headers,
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
