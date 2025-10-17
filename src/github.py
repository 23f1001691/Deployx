import subprocess
import asyncio
from pathlib import Path
import os
import httpx

class GitHubDeployer:
    """Handles GitHub repository creation and Pages deployment"""

    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token

    def clone_repository(self, repo_name: str, work_dir: Path) -> bool:
        """Clone existing repository"""
        try:
            repo_url = f"https://{self.token}@github.com/{self.username}/{repo_name}.git"
            subprocess.run(
                ["git", "clone", repo_url, str(work_dir)],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def read_repository_files(self, work_dir: Path) -> dict:
        """Read all files from repository"""
        files = {}
        for file_path in work_dir.rglob("*"):
            if file_path.is_file() and not any(
                part.startswith(".git") for part in file_path.parts
            ):
                rel_path = file_path.relative_to(work_dir)
                try:
                    # Try to read as text
                    content = file_path.read_text(encoding="utf-8")
                    files[str(rel_path)] = content
                except UnicodeDecodeError:
                    # Binary file, skip or handle differently
                    pass
        return files

    def update_repository(self, work_dir: Path, commit_message: str) -> str:
        """Update repository with changes"""

        # Configure git 
        subprocess.run(
            ["git", "config", "user.name", self.username],
            cwd=work_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", f"{self.username}@ds.study.iitm.ac.in"],
            cwd=work_dir,
            check=True,
        )

        # Add all changes
        subprocess.run(["git", "add", "."], cwd=work_dir, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            cwd=work_dir,
            capture_output=True
        )
        
        if result.returncode != 0:  # There are changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=work_dir,
                check=True,
            )
            
            # Push changes
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=work_dir,
                check=True,
            )

        # Get commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = result.stdout.strip()
        return commit_sha

    def create_repository(self, repo_name: str, work_dir: Path) -> tuple[str, str]:
        """Create GitHub repo and push code"""

        try:
            subprocess.run(["git", "init"], cwd=work_dir, check=True, capture_output=True)
            
            subprocess.run(
                ["git", "config", "user.name", self.username],
                cwd=work_dir,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", f"{self.username}@ds.study.iitm.ac.in"],
                cwd=work_dir,
                check=True,
                capture_output=True
            )

            subprocess.run(["git", "branch", "-M", "main"], cwd=work_dir, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=work_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=work_dir,
                check=True,
                capture_output=True
            )

            env = os.environ.copy()
            env["GH_TOKEN"] = self.token

            subprocess.run(
                ["gh", "repo", "create", repo_name, "--public", "--source=.", "--remote=origin", "--push"],
                cwd=work_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_sha = result.stdout.strip()

            repo_url = f"https://github.com/{self.username}/{repo_name}"
            return repo_url, commit_sha
            
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
            error_msg = f"Git/GitHub operation failed: {stderr}"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        except FileNotFoundError as e:
            error_msg = f"Command not found: {e.filename}. Ensure git and gh are installed."
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)

    def enable_pages(self, repo_name: str) -> str:
        """Enable GitHub Pages for repository"""

        env = os.environ.copy()
        env["GH_TOKEN"] = self.token

        # Enable Pages using gh CLI
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{self.username}/{repo_name}/pages",
                "-X",
                "POST",
                "-f",
                "source[branch]=main",
                "-f",
                "source[path]=/",
            ],
            env=env,
            check=True,
        )

        pages_url = f"https://{self.username}.github.io/{repo_name}/"
        return pages_url

    async def wait_for_pages(self, pages_url: str, max_wait: int = 300):
        """Wait for GitHub Pages to be available"""

        async with httpx.AsyncClient() as client:
            for i in range(max_wait // 10):
                try:
                    response = await client.get(pages_url, timeout=10)
                    if response.status_code == 200:
                        print(f"✅ Pages deployed successfully")
                        return True
                except Exception:
                    pass

                if i % 3 == 0:  # Log every 30 seconds
                    print(f"⏳ Waiting for Pages deployment... ({i*10}s)")

                await asyncio.sleep(10)

        print(f"⚠ Pages deployment timeout after {max_wait}s")
        return False