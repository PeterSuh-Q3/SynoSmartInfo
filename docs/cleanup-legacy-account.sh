#!/bin/sh
#
# cleanup-legacy-account.sh - remove the OS-level accounts that
# Syno Smart Info v2.0.0-v2.0.4 declared in conf/privilege
# ("sc-synosmartinfo" user, "synosmartinfo" group).
#
# Why this is needed: v2.0.5+ dropped those explicit declarations and
# went back to DSM's own auto-assigned package account (same as
# v1.4.2 always used). DSM never removes OS-level accounts on
# uninstall - they are not package files - so any device that ever
# ran v2.0.0-v2.0.4 keeps them forever. Their mere presence then
# breaks DSM's own auto-account provisioning for this package: the
# "Synosmartinfo" account DSM tries to create/reuse ends up bound to
# the leftover "synosmartinfo" group instead of getting a dedicated
# one, and every subsequent install/upgrade of v2.0.5+ - fresh
# installs included - fails with:
#
#   error 313 "failed to revise file attributes"
#
# This cannot be fixed by the package itself (preinst/postinst run as
# the package's own unprivileged account, not root, and DSM's
# installer refuses the conflicting-account case before invoking any
# package script in the first place - verified on real hardware). It
# has to be run manually, once, as root, before installing v2.0.5+.
#
# Usage (SSH into the NAS as an administrator, then):
#   sudo sh cleanup-legacy-account.sh
#
# Safe to run even if these accounts don't exist, or have already
# been cleaned up - both steps simply report nothing to do.

set -eu

if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root, e.g.: sudo sh $0" >&2
    exit 1
fi

for cmd in /usr/syno/sbin/synouser /usr/syno/sbin/synogroup; do
    if [ ! -x "$cmd" ]; then
        echo "Error: $cmd not found or not executable - is this a Synology NAS running DSM 7?" >&2
        exit 1
    fi
done

echo "==> Checking for the legacy 'sc-synosmartinfo' account..."
if /usr/syno/sbin/synouser --get sc-synosmartinfo >/dev/null 2>&1; then
    echo "    Found it - removing."
    /usr/syno/sbin/synouser --del sc-synosmartinfo
    echo "    Done."
else
    echo "    Not present, nothing to do."
fi

echo "==> Checking for the legacy 'synosmartinfo' group..."
if /usr/syno/sbin/synogroup --get synosmartinfo >/dev/null 2>&1; then
    echo "    Found it - removing."
    /usr/syno/sbin/synogroup --del synosmartinfo
    echo "    Done."
else
    echo "    Not present, nothing to do."
fi

echo "==> Cleanup complete. You can now install or upgrade to Syno Smart Info v2.0.5+."
