"""
GitHub Service for validating, checking accessibility, and cloning public repositories.
Supports git CLI shallow clone with an automatic ZIP download fallback.
"""
import io
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

import requests

from backend.utils.helpers import parse_github_url


class GitHubService:
    """Manages GitHub repository validation, accessibility checks, and local cloning."""

    def __init__(self, repos_dir: Optional[str] = None):
        if repos_dir:
            self.repos_dir = Path(repos_dir)
        else:
            base_dir = Path(__file__).resolve().parent.parent
            self.repos_dir = base_dir / "data" / "repos"

        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> Tuple[str, str]:
        """Validate format and extract (owner, repo). Raises ValueError on invalid format."""
        return parse_github_url(url)

    def check_accessibility(self, owner: str, repo: str) -> Tuple[bool, Optional[str]]:
        """
        Verify that the repository is public and accessible on GitHub.
        Returns (is_accessible, error_message).
        """
        url = f"https://github.com/{owner}/{repo}"
        headers = {"User-Agent": "GitHub-Codebase-RAG-Assistant/1.0"}

        try:
            # We use a HEAD request with allow_redirects=True to test public availability
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return True, None
            elif response.status_code == 404:
                return False, f"Repository '{owner}/{repo}' was not found. Please verify the URL and ensure the repository is public."
            elif response.status_code == 403:
                # Rate limit or access restricted
                return False, "Access to GitHub is temporarily restricted (rate limit exceeded). Please try again in a few minutes."
            else:
                return False, f"GitHub returned status code {response.status_code} when verifying repository."
        except requests.exceptions.Timeout:
            return False, "Connection to GitHub timed out. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            return False, f"Network error connecting to GitHub: {str(e)}"

    def get_repo_dir_name(self, owner: str, repo: str) -> str:
        """Return canonical local folder name for repository."""
        return f"{owner}__{repo}".lower()

    def get_repo_path(self, owner: str, repo: str) -> Path:
        """Return the Path to the local repository clone."""
        return self.repos_dir / self.get_repo_dir_name(owner, repo)

    def is_cached(self, owner: str, repo: str) -> bool:
        """Check if repository is already cloned locally and contains files."""
        repo_path = self.get_repo_path(owner, repo)
        if repo_path.exists() and repo_path.is_dir():
            # Check if directory has at least one file
            has_files = any(repo_path.iterdir())
            return has_files
        return False

    def clone_repository(
        self,
        github_url: str,
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Path:
        """
        Clones public GitHub repository into local storage.
        Uses git clone --depth 1 for speed. If git fails, falls back to downloading ZIP.
        
        Args:
            github_url: The public GitHub URL.
            force_reindex: If True, re-clones even if cached.
            progress_callback: Optional callback(step_message, percentage).
            
        Returns:
            Path: Absolute path to the cloned repository.
        """
        owner, repo = self.validate_url(github_url)

        # Accessibility check
        if progress_callback:
            progress_callback("Validating repository accessibility...", 10)
        accessible, error_msg = self.check_accessibility(owner, repo)
        if not accessible:
            raise ValueError(error_msg or "Repository could not be accessed.")

        target_dir = self.get_repo_path(owner, repo)

        # Check if already cached
        if not force_reindex and self.is_cached(owner, repo):
            if progress_callback:
                progress_callback("Repository found in local cache.", 25)
            return target_dir

        # Prepare clean target directory
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(f"Cloning {owner}/{repo} (shallow clone)...", 15)

        # Attempt 1: Git CLI shallow clone (fast, minimal bandwidth)
        git_success = False
        try:
            clone_cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                f"https://github.com/{owner}/{repo}.git",
                str(target_dir),
            ]
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and any(target_dir.iterdir()):
                git_success = True
                if progress_callback:
                    progress_callback("Repository cloned successfully via Git.", 25)
        except Exception:
            git_success = False

        # Attempt 2: Fallback to downloading ZIP archive from GitHub
        if not git_success:
            if progress_callback:
                progress_callback("Git clone failed or unavailable. Downloading ZIP archive...", 18)

            zip_success = False
            # Common default branches to try
            branches_to_try = ["main", "master"]
            headers = {"User-Agent": "GitHub-Codebase-RAG-Assistant/1.0"}

            for branch in branches_to_try:
                zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
                try:
                    response = requests.get(zip_url, headers=headers, timeout=60, stream=True)
                    if response.status_code == 200:
                        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                            # The zip has a root folder like repo-main/
                            root_prefix = z.namelist()[0].split("/")[0] if z.namelist() else ""
                            for member in z.infolist():
                                # Prevent zip slip
                                member_path = member.filename
                                if member_path.startswith(f"{root_prefix}/"):
                                    rel_name = member_path[len(root_prefix) + 1 :]
                                    if not rel_name or rel_name.endswith("/"):
                                        continue
                                    dest_file = target_dir / rel_name
                                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                                    with z.open(member) as src, open(dest_file, "wb") as dst:
                                        shutil.copyfileobj(src, dst)
                        zip_success = True
                        break
                except Exception:
                    continue

            if not zip_success or not any(target_dir.iterdir()):
                raise RuntimeError(
                    f"Failed to download repository '{owner}/{repo}'. Please check repository permissions."
                )

            if progress_callback:
                progress_callback("Repository ZIP extracted successfully.", 25)

        return target_dir

    def remove_repository(self, owner: str, repo: str) -> bool:
        """Remove a cached repository from local disk."""
        target_dir = self.get_repo_path(owner, repo)
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            return True
        return False
