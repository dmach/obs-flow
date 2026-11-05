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

cleanup() {
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
"${FLOW_BIN}" config review add --project openSUSE:Factory --type project --user admin
"${FLOW_BIN}" config review add --project openSUSE:Factory --type package --user dimstar
"${FLOW_BIN}" config review add --project devel:system --type project --user darix

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
echo "=== Test data population complete! ==="
if [[ "${AUTO_STARTED_SERVER}" -eq 1 ]]; then
    if [[ "${KEEP_SERVER}" -eq 1 ]]; then
        echo "Background server PID: ${SERVER_PID} (still running at ${OBS_FLOW_SERVER_URL})"
    fi
fi
