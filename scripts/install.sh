#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${ID:-}" != ubuntu ]]; then
  echo "Unsupported operating system: ${PRETTY_NAME:-unknown}. Only Ubuntu 22.04 and 24.04 are supported." >&2
  exit 1
fi

case "${VERSION_ID:-}" in
  22.04) VERSION=22 ;;
  24.04) VERSION=24 ;;
  *)
    echo "Unsupported Ubuntu version: ${VERSION_ID:-unknown}. Only Ubuntu 22.04 and 24.04 are supported." >&2
    exit 1
    ;;
esac

case "${1:-}" in
  '') SCRIPT="install_ubuntu_${VERSION}.sh" ;;
  --uninstall) SCRIPT="uninstall_ubuntu_${VERSION}.sh" ;;
  *)
    echo "Usage: $0 [--uninstall]" >&2
    exit 1
    ;;
esac

exec "$SCRIPT_DIR/install/$SCRIPT"
