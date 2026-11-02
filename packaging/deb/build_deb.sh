#!/usr/bin/env bash
# Build a Debian package for KaliForge.
#
# Usage:  packaging/deb/build_deb.sh [version]
#
# Produces  kaliforge_<version>_all.deb  in the repository root.
# The app is installed under /opt/kaliforge with a /usr/bin/kaliforge launcher,
# a desktop entry and an icon. Python dependencies are declared but PySide6 is
# large, so pip-install is recommended when apt packages are unavailable.
set -euo pipefail

VERSION="${1:-1.0.0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="${REPO_ROOT}/packaging/deb/build"
PKG="${BUILD}/kaliforge_${VERSION}_all"

echo ">> Cleaning previous build"
rm -rf "${BUILD}"
mkdir -p "${PKG}/DEBIAN" \
         "${PKG}/opt/kaliforge" \
         "${PKG}/usr/bin" \
         "${PKG}/usr/share/applications" \
         "${PKG}/usr/share/icons/hicolor/scalable/apps"

echo ">> Copying application files"
cd "${REPO_ROOT}"
for item in main.py config.json core ui tools database workflows plugins assets requirements.txt LICENSE README.md; do
    cp -r "${item}" "${PKG}/opt/kaliforge/"
done
find "${PKG}/opt/kaliforge" -name '__pycache__' -type d -prune -exec rm -rf '{}' +

echo ">> Installing launcher, desktop entry and icon"
cat > "${PKG}/usr/bin/kaliforge" <<'EOF'
#!/usr/bin/env bash
exec python3 /opt/kaliforge/main.py "$@"
EOF
chmod 755 "${PKG}/usr/bin/kaliforge"
cp packaging/kaliforge.desktop "${PKG}/usr/share/applications/kaliforge.desktop"
cp assets/kaliforge.svg "${PKG}/usr/share/icons/hicolor/scalable/apps/kaliforge.svg"

INSTALLED_SIZE=$(du -sk "${PKG}" | cut -f1)

echo ">> Writing control files"
cat > "${PKG}/DEBIAN/control" <<EOF
Package: kaliforge
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pyside6.qtwidgets | python3-pyqt6, python3-psutil
Recommends: python3-pip, nmap, whois, dnsutils
Suggests: wireshark, metasploit-framework
Installed-Size: ${INSTALLED_SIZE}
Maintainer: dipro20debnath
Homepage: https://github.com/dipro20debnath/KaliForge
Description: KaliForge — Cybersecurity Command Center
 An all-in-one security toolkit, integrated terminal, reconnaissance,
 vulnerability assessment, reporting and workflow automation dashboard
 for Kali Linux. One interface for every authorised-testing workflow.
EOF

cat > "${PKG}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
echo "KaliForge installed. If PySide6 is not available from apt, run:"
echo "    pip3 install --user PySide6 pyte reportlab"
exit 0
EOF
chmod 755 "${PKG}/DEBIAN/postinst"

if command -v dpkg-deb >/dev/null 2>&1; then
    echo ">> Building .deb"
    dpkg-deb --build --root-owner-group "${PKG}"
    mv "${PKG}.deb" "${REPO_ROOT}/kaliforge_${VERSION}_all.deb"
    echo ">> Built kaliforge_${VERSION}_all.deb"
else
    echo "!! dpkg-deb not found — package tree prepared at ${PKG}"
    echo "   Install dpkg-dev and re-run, or copy the tree manually."
fi
