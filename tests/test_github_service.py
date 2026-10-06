"""
Unit tests for GitHub URL validation and GitHubService.
"""
import pytest
from backend.services.github_service import GitHubService
from backend.utils.helpers import is_valid_github_url, parse_github_url


def test_parse_valid_github_urls():
    valid_cases = [
        ("https://github.com/torvalds/linux", ("torvalds", "linux")),
        ("https://github.com/psf/requests.git", ("psf", "requests")),
        ("https://www.github.com/fastapi/fastapi/", ("fastapi", "fastapi")),
        ("http://github.com/pallets/flask", ("pallets", "flask")),
    ]
    for url, expected in valid_cases:
        assert parse_github_url(url) == expected
        assert is_valid_github_url(url) is True


def test_parse_invalid_github_urls():
    invalid_cases = [
        "",
        "   ",
        "https://gitlab.com/owner/repo",
        "https://github.com/",
        "https://github.com/onlyowner",
        "not_a_url",
        "ftp://github.com/owner/repo",
    ]
    for url in invalid_cases:
        assert is_valid_github_url(url) is False
        with pytest.raises(ValueError):
            parse_github_url(url)


def test_github_service_instantiation(tmp_path):
    service = GitHubService(repos_dir=str(tmp_path))
    assert service.repos_dir.exists()
    assert service.get_repo_dir_name("owner", "repo") == "owner__repo"
