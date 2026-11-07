#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

FLOW_BIN="${FLOW_BIN:-${ROOT_DIR}/flow}"
SERVER_URL="${OBS_FLOW_SERVER_URL:-http://localhost:8000}"
TOKEN="${OBS_FLOW_TOKEN:-flow-admin}"
KEEP_SERVER="${KEEP_SERVER:-1}"

export OBS_FLOW_SERVER_URL="${SERVER_URL}"
export OBS_FLOW_TOKEN="${TOKEN}"

echo "=========================================================="
echo "          OBS Flow Test Data Population Script            "
echo "=========================================================="
echo "Target server: ${OBS_FLOW_SERVER_URL}"
echo "CLI wrapper:   ${FLOW_BIN}"

AUTO_STARTED_SERVER=0
SERVER_PID=""
TMP_WORK=""

cleanup() {
    if [[ -n "${TMP_WORK}" && -d "${TMP_WORK}" ]]; then
        rm -rf "${TMP_WORK}"
    fi
    if [[ "${AUTO_STARTED_SERVER}" -eq 1 && "${KEEP_SERVER}" -eq 0 && -n "${SERVER_PID}" ]]; then
        echo "Stopping temporary background server (PID ${SERVER_PID})..."
        kill "${SERVER_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

check_server() {
    curl -sf -X POST "${OBS_FLOW_SERVER_URL}/api/v1/project/list" \
        -H "Content-Type: application/json" \
        -d "{}" > /dev/null 2>&1
}

# Check if server is running; if not, attempt to start it
if ! check_server; then
    echo "Server not responding at ${OBS_FLOW_SERVER_URL}. Starting dev server..."
    uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py runbolt &
    SERVER_PID=$!
    AUTO_STARTED_SERVER=1

    echo "Waiting for server to become ready..."
    READY=0
    for i in {1..30}; do
        if check_server; then
            READY=1
            echo "Server is ready! (PID: ${SERVER_PID})"
            break
        fi
        sleep 0.5
    done

    if [[ "${READY}" -ne 1 ]]; then
        echo "Error: Server failed to start within 15 seconds."
        exit 1
    fi
else
    echo "Server is active at ${OBS_FLOW_SERVER_URL}."
fi

echo ""
echo "--- 1. Creating Organizations ---"
# Shared distro orgs
"${FLOW_BIN}" org create openSUSE
"${FLOW_BIN}" org create devel:languages:python
"${FLOW_BIN}" org create devel:system
"${FLOW_BIN}" org create devel:tools

# Personal orgs
"${FLOW_BIN}" org create "~tux" --user tux
"${FLOW_BIN}" org create "~geeko" --user geeko
"${FLOW_BIN}" org create "~alice" --user alice
"${FLOW_BIN}" org create "~bob" --user bob

echo ""
echo "--- 2. Creating Projects ---"
# Main distribution projects
"${FLOW_BIN}" project create openSUSE:Factory --org openSUSE --branch factory --workflow-type staging
"${FLOW_BIN}" project create openSUSE:Leap:16.1 --org openSUSE --branch leap-16.1 --workflow-type direct

# Devel projects
"${FLOW_BIN}" project create devel:languages:python --org devel:languages:python --branch master --workflow-type direct
"${FLOW_BIN}" project create devel:system --org devel:system --branch master --workflow-type direct
"${FLOW_BIN}" project create devel:tools --org devel:tools --branch master --workflow-type direct

# Personal projects
"${FLOW_BIN}" project create home:tux --org "~tux" --branch dev --workflow-type direct
"${FLOW_BIN}" project create home:geeko --org "~geeko" --branch main --workflow-type direct
"${FLOW_BIN}" project create home:alice --org "~alice" --branch work --workflow-type direct
"${FLOW_BIN}" project create home:bob --org "~bob" --branch feature --workflow-type direct

echo ""
echo "--- 3. Creating Packages and Native Git Repositories ---"
# Distribution packages in Factory
"${FLOW_BIN}" package create openSUSE:Factory python3
"${FLOW_BIN}" package create openSUSE:Factory systemd
"${FLOW_BIN}" package create openSUSE:Factory zypper
"${FLOW_BIN}" package create openSUSE:Factory glibc
"${FLOW_BIN}" package create openSUSE:Factory bash

# Distribution packages in Leap:16.1
"${FLOW_BIN}" package create openSUSE:Leap:16.1 zypper

# Devel project packages (forks from Factory and new packages)
"${FLOW_BIN}" package create devel:languages:python python3 --fork-from-project openSUSE:Factory --fork-from-package python3
"${FLOW_BIN}" package create devel:languages:python python-requests
"${FLOW_BIN}" package create devel:languages:python python-msgspec

"${FLOW_BIN}" package create devel:system systemd --fork-from-project openSUSE:Factory --fork-from-package systemd
"${FLOW_BIN}" package create devel:system udev

"${FLOW_BIN}" package create devel:tools osc

# Personal project packages (forks for user changes)
"${FLOW_BIN}" package create home:tux python3 --fork-from-project devel:languages:python --fork-from-package python3
"${FLOW_BIN}" package create home:tux my-app
"${FLOW_BIN}" package create home:geeko zypper --fork-from-project openSUSE:Factory --fork-from-package zypper
"${FLOW_BIN}" package create home:alice systemd --fork-from-project devel:system --fork-from-package systemd
"${FLOW_BIN}" package create home:bob bash --fork-from-project openSUSE:Factory --fork-from-package bash

echo ""
echo "--- 4. Configuring Reviewers ---"
"${FLOW_BIN}" config review add --project openSUSE:Factory --type project --user admin || true
"${FLOW_BIN}" config review add --project openSUSE:Factory --type package --user dimstar || true
"${FLOW_BIN}" config review add --project devel:system --type project --user darix || true

echo ""
echo "--- 4b. Seeding Git Commits and Branches for PR Demonstration ---"
GIT_ROOT="${ROOT_DIR}/packages/server/src/obs_flow_server/git_repos"
FACTORY_REPO="${GIT_ROOT}/openSUSE/python3.git"
TUX_REPO="${GIT_ROOT}/~tux/python3.git"

TMP_WORK="$(mktemp -d)"

if [[ -d "${FACTORY_REPO}" && -d "${TUX_REPO}" ]]; then
    # 1. Seed base commit in Factory python3 repo
    git clone "${FACTORY_REPO}" "${TMP_WORK}/factory_python3" 2>/dev/null || (mkdir -p "${TMP_WORK}/factory_python3" && cd "${TMP_WORK}/factory_python3" && git init && git remote add origin "${FACTORY_REPO}")
    pushd "${TMP_WORK}/factory_python3" > /dev/null
    git checkout -B factory
    cat << 'EOF' > python3.spec
Name:           python3
Version:        3.13.1
Release:        0
Summary:        Python 3 Interpreter
License:        Python-2.0
URL:            https://www.python.org/
Source0:        Python-%{version}.tar.xz
BuildRequires:  gcc
BuildRequires:  openssl-devel

%description
Python 3 is an interpreted, interactive, object-oriented programming language.

%prep
%setup -q -n Python-%{version}

%build
%configure
%make_build

%install
%make_install

%files
%{_bindir}/python3
EOF

    cat << 'EOF' > python3.changes
-------------------------------------------------------------------
Wed Dec 04 12:00:00 UTC 2024 - maintainer@opensuse.org

- Update to 3.13.1:
  * Maintenance release of Python 3.13
EOF

    cat << 'EOF' > README.md
# Python 3 Packaging for openSUSE:Factory

This repository contains the RPM packaging sources for Python 3 in openSUSE.
EOF

    git config user.name "Factory Maintainer"
    git config user.email "factory@opensuse.org"
    git add python3.spec python3.changes README.md
    git commit -m "python3: Initial package import for 3.13.1"
    git push origin factory
    popd > /dev/null

    # 2. Clone Tux personal repo, pull from factory, add commits
    git clone "${TUX_REPO}" "${TMP_WORK}/tux_python3" 2>/dev/null || (mkdir -p "${TMP_WORK}/tux_python3" && cd "${TMP_WORK}/tux_python3" && git init && git remote add origin "${TUX_REPO}")
    pushd "${TMP_WORK}/tux_python3" > /dev/null
    git checkout -B dev
    git pull "${FACTORY_REPO}" factory > /dev/null 2>&1 || true

    # Commit 1: Version bump to 3.13.2 in spec and changes
    sed -i 's/Version:        3.13.1/Version:        3.13.2/' python3.spec
    cat << 'EOF' > python3.changes
-------------------------------------------------------------------
Fri Feb 07 10:00:00 UTC 2025 - tux@opensuse.org

- Update to 3.13.2:
  * Security and bugfix release
  * Includes fix for CVE-2025-XXXX

-------------------------------------------------------------------
Wed Dec 04 12:00:00 UTC 2024 - maintainer@opensuse.org

- Update to 3.13.1:
  * Maintenance release of Python 3.13
EOF
    git config user.name "Tux Penguin"
    git config user.email "tux@opensuse.org"
    git add python3.spec python3.changes
    git commit -m "python3: Update to version 3.13.2"

    # Commit 2: Add SSL threading patch
    cat << 'EOF' > 0001-fix-ssl-threading.patch
From 11223344556677889900aabbccddeeff11223344 Mon Sep 17 00:00:00 2001
Subject: [PATCH] Fix race condition in SSL socket initialization

Signed-off-by: Tux Penguin <tux@opensuse.org>
---
 Modules/_ssl.c | 4 ++++
 1 file changed, 4 insertions(+)

diff --git a/Modules/_ssl.c b/Modules/_ssl.c
index 1234567..89abcdef 100644
--- a/Modules/_ssl.c
+++ b/Modules/_ssl.c
@@ -100,6 +100,10 @@ static int ssl_init(void) {
+    /* Ensure mutex lock before context init */
+    PySSL_LOCK();
     SSL_library_init();
+    PySSL_UNLOCK();
     return 0;
 }
-- 
2.48.1
EOF
    sed -i '/Source0:/a Patch0:         0001-fix-ssl-threading.patch' python3.spec
    git add 0001-fix-ssl-threading.patch python3.spec
    git commit -m "python3: Add 0001-fix-ssl-threading.patch for multi-threaded SSL"

    # Commit 3: Update documentation
    cat << 'EOF' >> README.md

## Upstream 3.13.2 Notes
Upstream release 3.13.2 addresses several thread safety issues under GIL-disabled configurations.
EOF
    git add README.md
    git commit -m "docs: Add packaging notes for 3.13.2 GIL behavior"

    git push -u origin dev
    popd > /dev/null
    echo "Successfully seeded 3 commits and 4 changed files for PR 1 demo."
fi

echo ""
echo "--- 5. Opening Native Pull Requests ---"
# PR 1: Tux updates Python 3 in openSUSE:Factory
"${FLOW_BIN}" pr create \
    --target-project openSUSE:Factory \
    --target-package python3 \
    --author tux \
    --title "Update Python 3 to 3.13.2" \
    --source-owner "~tux" \
    --source-repo python3 \
    --source-branch dev

# PR 2: Geeko fixes Zypper solver issue in openSUSE:Factory
"${FLOW_BIN}" pr create \
    --target-project openSUSE:Factory \
    --target-package zypper \
    --author geeko \
    --title "Resolve zypper solver dependency loop" \
    --source-owner "~geeko" \
    --source-repo zypper \
    --source-branch main

# PR 3: Alice contributes systemd patch to devel:system
"${FLOW_BIN}" pr create \
    --target-project devel:system \
    --target-package systemd \
    --author alice \
    --title "Improve systemd-oomd memory pressure detection" \
    --source-owner "~alice" \
    --source-repo systemd \
    --source-branch work

# PR 4: Bob submits bash patchset to openSUSE:Factory (as draft)
"${FLOW_BIN}" pr create \
    --target-project openSUSE:Factory \
    --target-package bash \
    --author bob \
    --title "WIP: Bash 5.3 upstream patchset" \
    --source-owner "~bob" \
    --source-repo bash \
    --source-branch feature \
    --draft

# PR 5: Tux submits project-level request to introduce python-requests to Factory
"${FLOW_BIN}" pr create \
    --target-project openSUSE:Factory \
    --author tux \
    --title "Introduce python-requests package to openSUSE:Factory" \
    --source-owner devel:languages:python \
    --source-repo python-requests \
    --source-branch master

echo ""
echo "--- 6. Adding Discussion Comments ---"
"${FLOW_BIN}" pr comment add --pr openSUSE/python3#1 --author geeko --body "Looks good! Did upstream backport the GIL fixes in 3.13.2?"
"${FLOW_BIN}" pr comment add --pr openSUSE/python3#1 --author tux --body "Yes, all upstream GIL fixes are included in this tarball."
"${FLOW_BIN}" staging comment add --batch 1 --author tux --body "Staging batch is collecting packages for Factory release tests."

echo ""
echo "=== Test data population complete! ==="
if [[ "${AUTO_STARTED_SERVER}" -eq 1 ]]; then
    if [[ "${KEEP_SERVER}" -eq 1 ]]; then
        echo "Background server PID: ${SERVER_PID} (still running at ${OBS_FLOW_SERVER_URL})"
    fi
fi
