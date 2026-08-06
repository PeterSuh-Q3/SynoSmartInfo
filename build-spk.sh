#!/bin/bash
#
# build-spk.sh - self-contained Synology .spk packer.
#
# Why this exists instead of Synology's pkgscripts-ng (or a wrapper
# around it): nothing in this package is compiled against Synology's
# toolchain. The only native code is the setuid helper, and that's
# built as a plain static binary with the host's own gcc (see below).
# pkgscripts-ng nonetheless insists on assembling packages inside a
# per-platform chroot, which meant downloading ~2GB of Synology
# toolchain tarballs from servers that frequently stall or truncate -
# pure overhead, and the source of several build failures. Ported from
# mshell-manager's build-spk.sh (same structure: package.json schema,
# conf/privilege "tool" section, setuid helper).
#
# An .spk is just a tar:
#     spk = tar{ INFO, conf/, scripts/, package.tgz, [icons], ... }
#     package.tgz = tar.gz{ contents of src/ -> becomes target/ }
# which is what this script builds directly.
#
# Usage: ./build-spk.sh [output-dir]      (default: ./dist)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$(cd "${1:-${ROOT}/dist}" 2>/dev/null || { mkdir -p "${1:-${ROOT}/dist}"; cd "${1:-${ROOT}/dist}"; }; pwd)"
CONFIG="${ROOT}/package.json"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

j() { jq -r "$1 // empty" "${CONFIG}"; }

# CI runs this on Linux; these keep it runnable on macOS too so the
# packaging logic can be exercised locally without burning a CI round.
md5_of() {
    if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | awk '{print $1}'
    else md5 -q "$1"; fi
}
b64_of() {
    # Read via stdin, not a positional filename argument: BSD base64
    # (macOS) rejects a filename arg outright ("invalid argument"),
    # while GNU base64 (CI, Linux) accepts either - stdin is the one
    # form both implementations agree on.
    if base64 --help 2>&1 | grep -q -- '-w,'; then base64 -w 0 < "$1"
    else base64 < "$1" | tr -d '\n'; fi
}

# Every entry in a real Synology-built .spk is owned by root:root.
# Without this, the archive records whoever ran the build - on CI that's
# uid 1001 "runner", which shows up in the installed package's file
# attributes and is visibly wrong next to any genuine package. The two
# tar flavors spell this differently and neither accepts the other's
# form, so pick per-flavor rather than assuming GNU.
if tar --version 2>/dev/null | grep -qi 'gnu tar'; then
    TAR_OWNER=(--owner=root --group=root)
else
    TAR_OWNER=(--uid 0 --gid 0 --uname root --gname root)
fi

PKG_NAME="$(j '.name')"
PKG_VERSION="$(j '.version')"
PKG_ARCH="$(j '.synology.arch')"
[ -n "${PKG_NAME}" ] || { echo "package.json: .name is required" >&2; exit 1; }
[ -n "${PKG_VERSION}" ] || { echo "package.json: .version is required" >&2; exit 1; }

echo "==> Building ${PKG_NAME} ${PKG_VERSION} (${PKG_ARCH:-noarch})"

# ---------------------------------------------------------------------
# 1. Compile the setuid helper.
#
# Statically linked with the host gcc on purpose: it must run on DSM
# without depending on whatever glibc that DSM ships, and it needs no
# Synology headers (it only uses setuid/execv/clearenv).
# ---------------------------------------------------------------------
HELPER_SRC="${ROOT}/synology/helper/smartinfo-helper.c"
if [ "${SKIP_HELPER:-0}" = "1" ]; then
    echo "==> SKIP_HELPER=1 - not compiling the helper (local structure test only)"
    mkdir -p "${ROOT}/src/bin/helper"
    : > "${ROOT}/src/bin/helper/smartinfo-helper.x86_64"
elif [ -f "${HELPER_SRC}" ]; then
    echo "==> Compiling setuid helper"
    mkdir -p "${ROOT}/src/bin/helper"
    gcc -O2 -static -Wall -Wextra \
        -o "${ROOT}/src/bin/helper/smartinfo-helper.x86_64" "${HELPER_SRC}"
    chmod 0755 "${ROOT}/src/bin/helper/smartinfo-helper.x86_64"
fi

# ---------------------------------------------------------------------
# 2. package.tgz - everything under src/ becomes the package's target/
# ---------------------------------------------------------------------
echo "==> Creating package.tgz"
STAGE="${BUILD_DIR}/target"
mkdir -p "${STAGE}"
cp -R "${ROOT}/src/." "${STAGE}/"
find "${STAGE}" -name '.DS_Store' -delete
chmod 0755 "${STAGE}/ui/api.cgi" 2>/dev/null || true
chmod 0755 "${STAGE}/bin/syno_smart_info.sh" 2>/dev/null || true

SPK_DIR="${BUILD_DIR}/spk"
mkdir -p "${SPK_DIR}"
tar "${TAR_OWNER[@]}" -czf "${SPK_DIR}/package.tgz" -C "${STAGE}" .

# DSM shows this as the install size; it's the uncompressed target/
# size in KB.
EXTRACT_SIZE="$(du -sk "${STAGE}" | awk '{print $1}')"
CHECKSUM="$(md5_of "${SPK_DIR}/package.tgz")"

# ---------------------------------------------------------------------
# 3. scripts/ and conf/ (these stay outside package.tgz)
# ---------------------------------------------------------------------
echo "==> Copying scripts/ and conf/"
cp -R "${ROOT}/synology/scripts" "${SPK_DIR}/scripts"
chmod 0755 "${SPK_DIR}/scripts/"*
[ -d "${ROOT}/synology/conf" ] && cp -R "${ROOT}/synology/conf" "${SPK_DIR}/conf" || true
for icon in PACKAGE_ICON.PNG PACKAGE_ICON_256.PNG; do
    [ -f "${ROOT}/synology/${icon}" ] && cp "${ROOT}/synology/${icon}" "${SPK_DIR}/${icon}" || true
done
[ -f "${ROOT}/LICENSE" ] && cp "${ROOT}/LICENSE" "${SPK_DIR}/LICENSE" || true

# ---------------------------------------------------------------------
# 4. INFO
#
# Field notes (all learned the hard way on real DSM 7.4.1 hardware,
# see docs/synology-spk-build-notes.md):
#   checksum  - md5 of package.tgz. Without it DSM rejects a manually
#               installed spk outright ("spk is not from synology").
#   ctl_stop  - "no" hides Package Center's Start/Stop toggle, which
#               is meaningless for a package with no daemon.
#   dsmappname- required for the DSM desktop app entry to register.
# ---------------------------------------------------------------------
echo "==> Writing INFO"
INFO="${SPK_DIR}/INFO"
{
    echo "package=\"${PKG_NAME}\""
    echo "version=\"${PKG_VERSION}\""
    echo "description=\"$(j '.description')\""
    echo "maintainer=\"$(j '.synology.maintainer')\""
    echo "maintainer_url=\"$(j '.synology.maintainer_url')\""
    echo "distributor=\"$(j '.synology.distributor')\""
    echo "distributor_url=\"$(j '.synology.distributor_url')\""
    echo "support_url=\"$(j '.synology.support_url')\""
    echo "helpurl=\"$(j '.synology.help_url')\""
    echo "os_min_ver=\"$(j '.synology.os_min_ver')\""
    echo "os_max_ver=\"$(j '.synology.os_max_ver')\""
    echo "arch=\"${PKG_ARCH:-noarch}\""
    echo "displayname=\"$(j '.synology.displayname')\""
    echo "thirdparty=\"$(j '.synology.thirdparty')\""
    echo "beta=\"$( [ "$(j '.synology.beta')" = "yes" ] && echo true || echo false )\""
    echo "dsmuidir=\"$(j '.dsmuidir')\""
    echo "dsmappname=\"$(j '.dsmappname')\""
    echo "install_dep_packages=\"$(j '.install_dep_packages')\""
    echo "ctl_stop=\"$(j '.ctl_stop')\""
    echo "ctl_uninstall=\"$(j '.ctl_uninstall')\""
    echo "support_conf_folder=\"$(j '.support_conf_folder')\""
    echo "extractsize=\"${EXTRACT_SIZE}\""
    echo "create_time=\"$(date +%Y%m%d-%H:%M:%S)\""
    echo "checksum=\"${CHECKSUM}\""
    for icon in "PACKAGE_ICON.PNG:package_icon" "PACKAGE_ICON_256.PNG:package_icon_256"; do
        f="${ROOT}/synology/${icon%%:*}"
        [ -f "$f" ] && echo "${icon##*:}=\"$(b64_of "$f")\"" || true
    done
} > "${INFO}"

# ---------------------------------------------------------------------
# 5. The spk itself. INFO must sort first, which it does alphabetically
#    (uppercase before lowercase) - matches how real toolkit-built
#    packages are laid out.
# ---------------------------------------------------------------------
SPK="${OUT_DIR}/${PKG_NAME}-${PKG_ARCH:-noarch}-${PKG_VERSION}.spk"
mkdir -p "${OUT_DIR}"
rm -f "${SPK}"
( cd "${SPK_DIR}" && tar "${TAR_OWNER[@]}" -cf "${SPK}" $(ls) )

echo "==> Built ${SPK}"
echo "    package.tgz md5 : ${CHECKSUM}"
echo "    extract size    : ${EXTRACT_SIZE} KB"
tar -tf "${SPK}"
