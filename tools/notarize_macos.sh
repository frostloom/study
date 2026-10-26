#!/bin/bash
# Run only after configuring your own Developer ID and notarytool keychain profile.
set -euo pipefail
: "${SIGN_IDENTITY:?Set SIGN_IDENTITY to your Developer ID Application identity}"
: "${NOTARY_PROFILE:?Set NOTARY_PROFILE to an existing notarytool keychain profile}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="${BUILD_DIST:-$ROOT/release-dist}"
APP="$DIST/日常学习.app"
[[ -d "$APP" ]] || { echo 'Build the app first.' >&2; exit 1; }
while IFS= read -r -d '' path; do
  if file -b "$path" | /usr/bin/grep -q 'Mach-O'; then codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY" "$path"; fi
done < <(find "$APP/Contents/Resources/backend" -type f -print0)
codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY" "$APP/Contents/MacOS/DailyStudy"
codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"
UPLOAD="$DIST/日常学习-notary-upload.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$UPLOAD"
xcrun notarytool submit "$UPLOAD" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
spctl --assess --type execute --verbose=2 "$APP"
ZIP="$DIST/日常学习-1.0.0-macOS-arm64.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/日常学习.app"
ln -s /Applications "$STAGE/Applications"
DMG="$DIST/日常学习-1.0.0-macOS-arm64.dmg"
rm -f "$DMG"
hdiutil create -volname '日常学习 1.0.0' -srcfolder "$STAGE" -format UDZO -ov "$DMG"
codesign --force --timestamp --sign "$SIGN_IDENTITY" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$DMG"
hdiutil verify "$DMG"
(cd "$DIST" && shasum -a 256 日常学习-1.0.0-macOS-arm64.zip 日常学习-1.0.0-macOS-arm64.dmg > SHA256SUMS.txt)
echo 'Developer ID signing and Apple notarization complete. Re-test the downloaded artifacts before public release.'
