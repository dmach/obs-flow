import base64
import os
import re
import xml.etree.ElementTree as ET
from pathlib import PurePath

import requests
import yaml
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Project, Package, GitMapping


class Command(BaseCommand):
    help = "Sync projects, packages, and git mappings from OBS and Gitea"

    def add_arguments(self, parser):
        parser.add_argument("--obs-api-url", default=os.environ.get("OBS_API_URL", "https://api.opensuse.org"))
        parser.add_argument("--obs-user", default=os.environ.get("OBS_USER", ""))
        parser.add_argument("--obs-password", default=os.environ.get("OBS_PASSWORD", ""))
        parser.add_argument("--gitea-url", default=os.environ.get("GIT_OBS_GITEA_URL", "https://src.opensuse.org"))
        parser.add_argument("--gitea-token", default=os.environ.get("GIT_OBS_GITEA_TOKEN", ""))

    def handle(self, *args, **options):
        """
        Main entry point for the management command.
        Fetches projects from OBS and triggers processing for each.
        """
        obs_api_url = options["obs_api_url"].rstrip("/")
        obs_user = options["obs_user"]
        obs_password = options["obs_password"]
        gitea_url = options["gitea_url"].rstrip("/")
        gitea_token = options["gitea_token"]

        self.stdout.write("Fetching projects from OBS...")
        headers = {}
        if obs_user and obs_password:
            auth = base64.b64encode(f"{obs_user}:{obs_password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"

        search_url = f"{obs_api_url}/search/project?match=scmsync"
        try:
            response = requests.get(search_url, headers=headers, timeout=30)
            response.raise_for_status()
        except Exception as e:
            self.stderr.write(f"Failed to fetch from OBS: {e}")
            return

        root = ET.fromstring(response.content)
        projects = []
        for proj_node in root.findall("project"):
            name = proj_node.get("name")
            if not name:
                continue

            if name.startswith("home:") or ":PullRequest:" in name or ":PR-" in name or "PTF" in name:
                continue

            scmsync_node = proj_node.find("scmsync")
            if scmsync_node is None or not scmsync_node.text:
                continue

            projects.append({"name": name, "scmsync": scmsync_node.text})

        self.stdout.write(f"Found {len(projects)} projects with scmsync.")

        gitea_headers = {}
        if gitea_token:
            gitea_headers["Authorization"] = f"token {gitea_token}"

        for proj_data in projects:
            self.process_project(proj_data["name"], proj_data["scmsync"], gitea_url, gitea_headers)

    def process_project(self, obs_project, scmsync_url, gitea_url, gitea_headers):
        """
        Processes a single OBS project by parsing its scmsync URL,
        fetching its Gitea repository tree, and identifying packages and submodules.
        """
        self.stdout.write(f"Processing {obs_project}...")

        match = re.match(
            r"^(https?://)?([^/]+)/([^/]+)/([^\/\#\.]+?)(\.git)?(\?[^#\/]*)?(\#([^\/#]+))?$",
            scmsync_url,
        )
        if not match:
            self.stderr.write(f"Invalid repo url: {scmsync_url}")
            return

        proto = match.group(1) or "https://"
        host = match.group(2)
        org = match.group(3)
        repo = match.group(4)
        branch = match.group(8)

        req_url = f"{proto}{host}/api/v1/repos/{org}/{repo}"
        try:
            response = requests.get(req_url, headers=gitea_headers, timeout=30)
            response.raise_for_status()
        except Exception as e:
            self.stderr.write(f"Failed to fetch repo info for {org}/{repo}: {e}")
            return

        data = response.json()
        if not branch:
            branch = data.get("default_branch", "main")

        tree_url = f"{proto}{host}/api/v1/repos/{org}/{repo}/git/trees/{branch}"
        body, sha, truncated = self.git_tree_request(tree_url, gitea_headers)
        if not body:
            return

        subdirs = None
        workflow_config_url = None
        for r in body:
            path = r.get("path", "")
            if path in ("_subdirs", "_manifest"):
                subdirs = self.process_manifest_from_url(r["url"], gitea_headers)
            elif path == "workflow.config":
                workflow_config_url = r["url"]

        workflow_config_branch = None
        if workflow_config_url:
            workflow_config_branch = self.process_workflow_config_from_url(workflow_config_url, gitea_headers)

        recursive = False
        if subdirs:
            recursive = True
            body, sha, truncated = self.git_tree_request(tree_url + "?recursive=1", gitea_headers)

        package_sha = {}
        submodule_branches = {}

        page = 0
        while True:
            for r in body:
                path = r.get("path", "")
                if not path:
                    continue

                if path == ".gitmodules":
                    submodule_branches = self.collect_branches_from_gitmodules_url(
                        r["url"], gitea_headers, subdirs, host, org
                    )
                    continue

                if subdirs:
                    path_obj = PurePath(path)
                    parent = str(path_obj.parent)
                    if parent not in subdirs:
                        continue

                if r.get("mode") == "160000" and r.get("type") == "commit":
                    package_sha[path] = r.get("sha", "")
                elif r.get("mode") == "040000" and r.get("type") == "tree":
                    package_sha[path] = ""
                    submodule_branches[path] = ("", "", "", "")

            if not truncated:
                break

            page += 1
            next_url = f"{tree_url}?recursive=1&page={page}" if recursive else f"{tree_url}?page={page}"
            body, sha, truncated = self.git_tree_request(next_url, gitea_headers)
            if not body:
                break

        # Apply fallback logic for missing submodule branches
        # 1. Try to use Branch from workflow.config
        if workflow_config_branch:
            for path, tpl in submodule_branches.items():
                if tpl[0] and not tpl[3]:  # actual submodule, but empty branch
                    submodule_branches[path] = (tpl[0], tpl[1], tpl[2], workflow_config_branch)

        # 2. Fallback to rule based on other packages (if still empty)
        non_empty_branches = {tpl[3] for tpl in submodule_branches.values() if tpl[0] and tpl[3]}
        if len(non_empty_branches) == 1:
            common_branch = list(non_empty_branches)[0]
            for path, tpl in submodule_branches.items():
                if tpl[0] and not tpl[3]:
                    submodule_branches[path] = (tpl[0], tpl[1], tpl[2], common_branch)

        self.save_to_db(obs_project, org, repo, branch, package_sha, submodule_branches)

    def git_tree_request(self, url, headers):
        """
        Helper to request a git tree from Gitea.
        Returns (tree, sha, truncated).
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("tree"), data.get("sha"), data.get("truncated")
        except Exception as e:
            self.stderr.write(f"Failed to fetch git tree from {url}: {e}")
            return None, None, None

    def process_manifest_from_url(self, url, headers):
        """
        Fetches and parses a manifest file (_manifest or _subdirs) from Gitea.
        Returns a list of subdirectories.
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            manifest = yaml.safe_load(content)
            if not manifest:
                return []
            subdirs = manifest.get("subdirectories") or manifest.get("subdirs") or []
            return [s for s in subdirs if s]
        except Exception as e:
            self.stderr.write(f"Failed to process manifest from {url}: {e}")
            return []

    def process_workflow_config_from_url(self, url, headers):
        """
        Fetches and parses workflow.config from Gitea.
        Returns the Branch value if found, otherwise None.
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            import json

            config = json.loads(content)
            return config.get("Branch")
        except Exception as e:
            self.stderr.write(f"Failed to process workflow.config from {url}: {e}")
            return None

    def collect_branches_from_gitmodules_url(self, url, headers, subdirs, default_host, default_org):
        """
        Fetches and parses .gitmodules file from Gitea.
        Returns a mapping of submodule path to (host, org, repo, branch).
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            from configparser import ConfigParser

            cfg = ConfigParser()
            cfg.read_string(content)

            res = {}
            for section in cfg.sections():
                if not section.startswith('submodule "'):
                    continue
                path = cfg.get(section, "path", fallback="")
                if not path:
                    continue

                if subdirs:
                    path_obj = PurePath(path)
                    parent = str(path_obj.parent)
                    if parent not in subdirs:
                        continue

                url_val = cfg.get(section, "url", fallback="")
                if not url_val:
                    continue

                match = re.match(
                    r"^(((https?:\/\/)?(.*@)?([^\/]+|..(\/..)?))\/([^\/]+)|..)\/([^\/\#]+?)(\.git)?$",
                    url_val,
                )
                if not match:
                    continue

                repo = match.group(8)
                org = match.group(7)
                host = match.group(6)

                if not host or host == "/..":
                    host = default_host
                if not org:
                    org = default_org
                if not repo:
                    continue

                branch = cfg.get(section, "branch", fallback="")
                res[path] = (host, org, repo, branch)

            return res
        except Exception as e:
            self.stderr.write(f"Failed to collect branches from gitmodules: {e}")
            return {}

    def save_to_db(self, obs_project, org, repo, branch, package_sha, submodule_branches):
        """
        Saves the project, packages, and git mappings to the database.
        Uses transaction.atomic to ensure data integrity.
        """
        with transaction.atomic():
            project, _ = Project.objects.get_or_create(name=obs_project)

            existing = GitMapping.objects.filter(owner__iexact=org, repo__iexact=repo, branch=branch).first()
            if existing and existing.project != project:
                if hasattr(project, "git_mapping") and project.git_mapping and project.git_mapping != existing:
                    project.git_mapping.delete()
                existing.project = project
                existing.package = None
                existing.owner = org
                existing.repo = repo
                existing.branch = branch
                existing.save()
            else:
                GitMapping.objects.update_or_create(
                    project=project, defaults={"owner": org, "repo": repo, "branch": branch, "package": None}
                )

            for pkg_path in sorted(package_sha.keys()):
                pkg_obj = PurePath(pkg_path)
                name = str(pkg_obj.name)
                if name.startswith("."):
                    continue

                package, _ = Package.objects.get_or_create(project=project, name=name)

                tpl = submodule_branches.get(pkg_path)
                if tpl:
                    pkg_host, pkg_org, pkg_repo, pkg_branch = tpl
                    if pkg_org and pkg_repo:
                        existing_pkg = GitMapping.objects.filter(
                            owner__iexact=pkg_org, repo__iexact=pkg_repo, branch=pkg_branch
                        ).first()
                        if existing_pkg and existing_pkg.package != package:
                            if (
                                hasattr(package, "git_mapping")
                                and package.git_mapping
                                and package.git_mapping != existing_pkg
                            ):
                                package.git_mapping.delete()
                            existing_pkg.package = package
                            existing_pkg.project = None
                            existing_pkg.owner = pkg_org
                            existing_pkg.repo = pkg_repo
                            existing_pkg.branch = pkg_branch
                            existing_pkg.save()
                        else:
                            GitMapping.objects.update_or_create(
                                package=package,
                                defaults={"owner": pkg_org, "repo": pkg_repo, "branch": pkg_branch, "project": None},
                            )
