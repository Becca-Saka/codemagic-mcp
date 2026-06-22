# Code signing

> Docs: https://docs.codemagic.io/yaml-code-signing/

**Never inline a certificate, keystore, or private key in the yaml.** Reference uploaded identities or
env var groups. Mark every signing secret as **Secret** in Codemagic. Use `get_team_signing(team_id)`
to see what's already uploaded and whether a profile's `bundle_id` matches the app.

Distribution types: `app_store` (App Store / TestFlight) · `ad_hoc` (Firebase / third-party) ·
`development` · `enterprise`. CLI `--type` equivalents: `IOS_APP_STORE`, `IOS_APP_ADHOC`,
`IOS_APP_DEVELOPMENT`, `IOS_IN_HOUSE`.

## iOS — pick ONE method

### automatic — App Store Connect API integration (recommended)
Codemagic fetches/creates certs + profiles from Apple at build time.
- Needs: an App Store Connect key added under **Team Settings → Integrations → Developer Portal**, and a
  `CERTIFICATE_PRIVATE_KEY` secret (generate: `ssh-keygen -t rsa -b 2048 -m PEM -f key -q -N ""`).
- **DO NOT add an `environment: ios_signing:` block** for this method — that block is only for
  codemagic-managed; mixing them fails the build.
```yaml
environment:
  groups: [code-signing]          # holds CERTIFICATE_PRIVATE_KEY
integrations:
  app_store_connect: <key_name>   # must match the Team Settings key name
scripts:
  - script: keychain initialize
  - script: app-store-connect fetch-signing-files "$(xcode-project detect-bundle-id)" --type IOS_APP_STORE --create
  - script: keychain add-certificates
  - script: xcode-project use-profiles
```

### codemagic-managed — certs/profiles uploaded in the Codemagic UI
Uses the `ios_signing` block; Codemagic injects the matching uploaded files.
```yaml
environment:
  ios_signing:
    distribution_type: app_store
    bundle_identifier: com.example.app   # must EXACTLY match the app's real bundle id
```
- **DON'T** also set `provisioning_profiles:`/`certificates:` here — using `distribution_type`/
  `bundle_identifier` (auto-match) together with explicit references is not allowed.
- A defined bundle id also fetches extension profiles (e.g. `com.example.app.NotificationService`).

### manual — base64 env vars
Secrets in a group (e.g. `appstore_credentials`): `CM_CERTIFICATE` (base64 `.p12`),
`CM_CERTIFICATE_PASSWORD` (if set), `CM_PROVISIONING_PROFILE` (base64 `.mobileprovision`). Scripts:
`keychain initialize` → write the profile to `~/Library/MobileDevice/Provisioning Profiles` →
`keychain add-certificates` → `xcode-project use-profiles`.

**iOS do's & don'ts**
- DO run `xcode-project use-profiles` before the build; place signing scripts after dependency install.
- DON'T fetch certificates that have no private key — Codemagic can't use them.
- DON'T reuse invalidated profiles after changing the app id or capabilities — regenerate.

## macOS
Uses the **same `ios_signing` key** as iOS. Certificate types: `MAC_APP_STORE`, `MAC_APP_DEVELOPMENT`,
`DEVELOPER_ID_APPLICATION` (outside the store), `MAC_INSTALLER_DISTRIBUTION`. Same three methods as iOS.
- Outside the Mac App Store → **notarize** after signing: `productbuild`/`productsign` the `.pkg`, then
  `xcrun notarytool submit` and `xcrun stapler staple`.

## Android — `android_signing`
Reference an uploaded keystore by name:
```yaml
environment:
  android_signing:
    - keystore_reference     # name must match the UI upload
```
Codemagic injects `CM_KEYSTORE_PATH`, `CM_KEYSTORE_PASSWORD`, `CM_KEY_ALIAS`, `CM_KEY_PASSWORD`.
- **Gradle must consume those vars in CI.** If `build.gradle` only reads `key.properties`, CI ships an
  unsigned/debug build. Add a `CI` guard (Codemagic exports `CI=true`) so CI uses the `CM_*` env vars
  while local builds keep using `key.properties` — patch only the `signingConfigs { release { … } }`
  block, don't rewrite the file.
- DON'T expect to download the keystore back from Codemagic — it can't be retrieved; keep a backup.
- DO use the same keystore for all Google Play releases.

## iOS simulator builds — no signing
For simulator-only test builds, skip signing entirely:
`xcodebuild ... -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=""`
(artifact is an unsigned `.app`, not an `.ipa`).

## Other frameworks
The iOS/Android/macOS blocks above are the same regardless of framework — only the **build command**
differs. So:
- **React Native / Flutter / Unity / .NET MAUI → iOS or Android**: use the matching iOS/Android section.
- **Unity** also needs a license group: `UNITY_EMAIL`, `UNITY_SERIAL`, `UNITY_PASSWORD` (Secret).
- **Windows (MSIX / Microsoft Store)**: package with the `msix` config; store creds in a group
  (`MS_STORE_ID`, `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`). See the publishing docs.

Confirm exact keys/flags against the docs and the official sample projects before committing.
