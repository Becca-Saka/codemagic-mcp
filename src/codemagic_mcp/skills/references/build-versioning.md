# Build versioning

> Docs: https://docs.codemagic.io/knowledge-codemagic/build-versioning/

Use when the user wants automatic build-number increments for App Store / TestFlight, Google Play, or
Firebase App Distribution uploads. Put the versioning script **before** the build step.

## Strategies (pick one per platform)
- **Codemagic counter** — `BUILD_NUMBER` (total builds for this workflow) or `PROJECT_BUILD_NUMBER`
  (total builds for the app, all workflows).
- **Store latest + 1** — fetch the latest with the Codemagic CLI, then increment:
  - App Store / TestFlight: `app-store-connect get-latest-app-store-build-number "$APP_APPLE_ID"`
    (needs `APP_STORE_CONNECT_*` keys + `APP_APPLE_ID`).
  - Google Play: `google-play get-latest-build-number --package-name "$PACKAGE_NAME"`.
  - Firebase: `firebase-app-distribution get-latest-build-version -p "$FIREBASE_PROJECT_ID" -a "$FIREBASE_APP_ID"`.
- **Manual / pubspec** — version lives in the project; CI only bumps the build number.

## Apply per project type
- **Flutter** — pass the number through the build:
  `flutter build appbundle --release --build-name=1.0.$PROJECT_BUILD_NUMBER --build-number=$PROJECT_BUILD_NUMBER`
  (same for `flutter build ipa`). Map `CFBundleVersion`/`CFBundleShortVersionString` to
  `$(FLUTTER_BUILD_NUMBER)`/`$(FLUTTER_BUILD_NAME)` in `Info.plist`.
- **Native iOS** — `cd ios && agvtool new-version -all $BUILD_NUMBER`.
- **Native Android** — pass `-PversionCode`/`-PversionName` to Gradle.

## Rules
- For a first-ever store upload (no prior build), use a counter or a fixed offset
  (e.g. `$(($PROJECT_BUILD_NUMBER + 200))`).
- Name the env groups / integrations the strategy needs, and confirm exact CLI flags against the docs.
