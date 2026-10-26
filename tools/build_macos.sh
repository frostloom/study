#!/bin/bash
set -euo pipefail
# Build from a clean source checkout. Never add the app-data or legacy directories.
SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SOURCE_ROOT"
PYTHON="${BUILD_PYTHON:-python3}"
DIST="${BUILD_DIST:-$SOURCE_ROOT/release-dist}"
BUILD="${BUILD_WORK:-$SOURCE_ROOT/release-build}"
SWIFT_CACHE="${BUILD_SWIFT_CACHE:-$BUILD/swift-module-cache}"
ARCH="$(uname -m)"
case "$ARCH" in arm64) ASSET_ARCH=arm64 ;; x86_64) ASSET_ARCH=x64 ;; *) echo 'Unsupported Mac architecture' >&2; exit 1 ;; esac
CHANNEL="${BUILD_CHANNEL:-stable}"
APP_NAME=日常学习
SWIFT_FLAGS=(-D RELEASE)
if [[ "$CHANNEL" == preview ]]; then APP_NAME=日常学习预览版; SWIFT_FLAGS=(-D PREVIEW); ASSET_ARCH="${ASSET_ARCH}-preview"; fi
if ! command -v "$PYTHON" >/dev/null 2>&1; then echo 'Set BUILD_PYTHON to a Python 3.12 environment with requirements-build.txt installed.' >&2; exit 1; fi
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"; import PyInstaller, certifi, pypdf'
VERSION="$("$PYTHON" -c 'from app_info import VERSION; print(VERSION)')"
mkdir -p "$DIST" "$BUILD"
export PYINSTALLER_CONFIG_DIR="$BUILD/pyinstaller-cache"
APP="$DIST/$APP_NAME.app"
# Only our known generated paths are replaced, never user data.
rm -rf "$APP" "$BUILD/pyinstaller" "$BUILD/backend-dist"
rm -f "$DIST/DailyStudy-${VERSION}-macos-${ASSET_ARCH}.dmg"
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir --name study-backend \
  --distpath "$BUILD/backend-dist" --workpath "$BUILD/pyinstaller" --specpath "$BUILD" \
  --add-data "$SOURCE_ROOT/static:static" --collect-data certifi --collect-data tzdata --hidden-import tzdata --hidden-import pypdf \
  "$SOURCE_ROOT/backend_entry.py"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$SOURCE_ROOT/native/Info.plist" "$APP/Contents/Info.plist"
"$PYTHON" - "$APP/Contents/Info.plist" "$VERSION" "$CHANNEL" "$APP_NAME" <<'PLIST'
import plistlib,sys
p,version,channel,name=sys.argv[1:]
with open(p,'rb') as f:info=plistlib.load(f)
info.update(CFBundleShortVersionString=version,CFBundleVersion=version,CFBundleName=name,CFBundleDisplayName=name)
if channel=='preview':info['CFBundleIdentifier']+='.'+channel
with open(p,'wb') as f:plistlib.dump(info,f)
PLIST
cp -R "$BUILD/backend-dist/study-backend" "$APP/Contents/Resources/backend"
"$PYTHON" - "$APP/Contents/Resources/ThirdPartyLicenses" <<'PYLICENSE'
import importlib.metadata as metadata
import pathlib
import shutil
import sys
import sysconfig
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
notes = []
for name in ('pyinstaller', 'certifi', 'pypdf', 'tzdata'):
    dist = metadata.distribution(name)
    notes.append(f"{dist.metadata['Name']} {dist.version}: {dist.metadata.get('License-Expression') or dist.metadata.get('License', '')}")
    for rel in dist.files or ():
        if any(word in str(rel).lower() for word in ('license', 'copying', 'copyright')):
            source = pathlib.Path(dist.locate_file(rel))
            if source.is_file():
                target = out / name / pathlib.Path(str(rel))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
(out / 'README.txt').write_text('Python 3.12 and third-party runtime components.\n' + '\n'.join(notes) + '\nPyInstaller bootloader distribution exception applies; see bundled license.\n', encoding='utf-8')
for location in (pathlib.Path(sysconfig.get_path('stdlib'))/'LICENSE.txt', pathlib.Path(sys.base_prefix)/'LICENSE.txt', pathlib.Path(sys.base_prefix)/'Resources/English.lproj/License.rtf'):
    if location.is_file(): shutil.copy2(location, out / ('Python-' + location.name))
PYLICENSE
# SDK 27 requires Swift 6.4; this machine has Swift 6.3 and a compatible 26.5 SDK.
SDK="${BUILD_SDK:-$(xcrun --show-sdk-path)}"
if [[ -z "${BUILD_SDK:-}" && -d /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk ]]; then
  SDK=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
fi
SWIFTC="$(xcrun --find swiftc)"
"$SWIFTC" "$SOURCE_ROOT/native/main.swift" "${SWIFT_FLAGS[@]}" -O -sdk "$SDK" -module-cache-path "$SWIFT_CACHE" -target "$ARCH-apple-macos13.0" \
  -framework AppKit -framework WebKit -o "$APP/Contents/MacOS/DailyStudy"
"$SWIFTC" "$SOURCE_ROOT/native/make_icon.swift" -O -sdk "$SDK" -module-cache-path "$SWIFT_CACHE" -target "$ARCH-apple-macos13.0" \
  -framework AppKit -o "$BUILD/make-icon"
"$BUILD/make-icon" "$BUILD/AppIcon.iconset"
iconutil -c icns "$BUILD/AppIcon.iconset" -o "$APP/Contents/Resources/AppIcon.icns"
# Re-sign every embedded Mach-O after assembling. Keep PyInstaller's dylib layout intact.
while IFS= read -r -d '' path; do
  if file -b "$path" | /usr/bin/grep -q 'Mach-O'; then codesign --force --sign - --timestamp=none "$path"; fi
done < <(find "$APP/Contents/Resources/backend" -type f -print0)
codesign --force --sign - --timestamp=none "$APP/Contents/MacOS/DailyStudy"
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"
"$PYTHON" -m pip freeze > "$DIST/build-environment.txt"
{ "$SWIFTC" --version; echo "SDK: $SDK"; sw_vers; echo "Architecture: $ARCH"; echo "Minimum macOS: 13.0"; echo "Signature: ad-hoc (not notarized)"; } >> "$DIST/build-environment.txt"
ZIP="$DIST/DailyStudy-${VERSION}-macos-${ASSET_ARCH}.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
if [[ "${1:-}" != --skip-dmg ]]; then
  STAGE="$BUILD/dmg-stage"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  cp -R "$APP" "$STAGE/$APP_NAME.app"
  ln -s /Applications "$STAGE/Applications"
  cp "$SOURCE_ROOT/docs/usage.md" "$STAGE/安装与构建说明.md"
  rm -f "$DIST/DailyStudy-${VERSION}-macos-${ASSET_ARCH}.dmg"
  hdiutil create -volname "$APP_NAME $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DIST/DailyStudy-${VERSION}-macos-${ASSET_ARCH}.dmg"
fi
(cd "$DIST" && find . -maxdepth 1 -type f \( -name "*.zip" -o -name "*.dmg" \) -exec shasum -a 256 {} \; > SHA256SUMS.txt)
echo "Built: $APP"
