#!/bin/sh
#
# Download every OBS group (members and group maintainers) as raw XML.
#
# Usage: scripts/fetch_obs_groups.sh [-A APIURL]
#
# Runs osc with the credentials of the user's osc configuration: reading groups
# requires an authenticated OBS account.
#
# Output, in scripts/obs_groups_cache/ (ignored by git: the data is not public):
#   groups.xml          response of GET /group
#   group-<title>.xml   response of GET /group/<title>, one file per group
#   MANIFEST            format, source, apiurl, fetched_at, groups (count)
#
# The directory is replaced only when every request succeeds. On any failure the
# script exits non-zero and leaves the previous download untouched.

set -eu

# Version of the output layout described above, written to MANIFEST. Readers
# must reject formats they do not know: bump it whenever the layout changes.
FORMAT=1
DEFAULT_APIURL=https://api.opensuse.org

usage() {
    echo "usage: $0 [-A APIURL]" >&2
    exit 2
}

die() {
    echo "error: $*" >&2
    exit 1
}

apiurl=$DEFAULT_APIURL
while getopts A:h opt; do
    case $opt in
        A) apiurl=$OPTARG ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))
[ $# -eq 0 ] || usage

command -v osc > /dev/null 2>&1 || die "osc not found"

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
out=$script_dir/obs_groups_cache

if [ -e "$out" ] && [ ! -f "$out/MANIFEST" ]; then
    die "$out exists and is not a previous download; refusing to replace it"
fi

tmp=$(mktemp -d "$out.new.XXXXXX")
old=
cleanup() {
    rm -rf -- "$tmp"
    if [ -n "$old" ]; then
        rm -rf -- "$old"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

fetch() {
    # $1: API path, $2: output file
    if ! osc -A "$apiurl" api "$1" < /dev/null > "$2" 2> "$tmp/osc.err"; then
        die "GET $1 failed: $(head -n 1 "$tmp/osc.err")"
    fi
}

fetch /group "$tmp/groups.xml"

expected=$(sed -n 's/.*<directory count="\([0-9][0-9]*\)".*/\1/p' "$tmp/groups.xml")
[ -n "$expected" ] || die "GET /group: no group count in the response"

tr '<' '\n' < "$tmp/groups.xml" | sed -n 's/^entry name="\([^"]*\)".*/\1/p' > "$tmp/names"
found=$(wc -l < "$tmp/names" | tr -d ' ')
[ "$found" -eq "$expected" ] || die "GET /group: announces $expected groups, lists $found"

while IFS= read -r title; do
    # OBS group titles are [A-Za-z0-9_.-]; anything else is unsafe as a file name.
    case $title in
        '' | *[!A-Za-z0-9_.-]* | . | ..) die "unexpected group title: '$title'" ;;
    esac
    fetch "/group/$title" "$tmp/group-$title.xml"
    grep -q '<group' "$tmp/group-$title.xml" || die "GET /group/$title: not a group"
done < "$tmp/names"
rm -f -- "$tmp/names" "$tmp/osc.err"

{
    echo "format=$FORMAT"
    echo "source=osc"
    echo "apiurl=$apiurl"
    echo "fetched_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "groups=$expected"
} > "$tmp/MANIFEST"

if [ -e "$out" ]; then
    old=$out.old.$$
    mv -- "$out" "$old"
fi
if ! mv -- "$tmp" "$out"; then
    if [ -n "$old" ] && mv -- "$old" "$out"; then
        old=
    fi
    die "could not move the download into $out"
fi
echo "$expected groups from $apiurl in $out"
