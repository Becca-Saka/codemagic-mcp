# Code signing

> Docs: https://docs.codemagic.io/yaml-code-signing/

**Never inline a certificate, keystore, or private key in the yaml.** Reference uploaded identities or
env var groups. Mark every signing secret as **Secret** in Codemagic. Use `get_team_signing(team_id)`
to see what's already uploaded and whether a profile's `bundle_id` matches the app.

Distribution types: `app_store` (App Store / TestFlight) · `ad_hoc` (Firebase / third-party) ·
`development` · `enterprise`. CLI `--type` equivalents: `IOS_APP_STORE`, `IOS_APP_ADHOC`,
`IOS_APP_DEVELOPMENT`, `IOS_IN_HOUSE`.

## iOS — pick ONE of three methods

All three end with `xcode-project use-profiles` (sets the signing settings on the Xcode project before
the build). They differ in *where the certificate + profile come from*.

### 1. ASC — automatic, App Store Connect API integration (recommended)
Codemagic fetches (or creates) the certs + profiles from Apple at build time using an App Store Connect
API key, driven by the `app-store-connect` CLI in scripts.
- Needs: an App Store Connect key added under **Team Settings → Integrations → Developer Portal /
  App Store Connect**, referenced by the workflow-level `integrations: app_store_connect: <key_name>`.
- **When using ASC automatic signing there must be NO `ios_signing` block** — the two must not be
  combined for signing. (An `app_store_connect` integration may otherwise coexist with `ios_signing`,
  e.g. when the integration is only used for publishing — just not to drive signing.)
```yaml
integrations:                              # workflow-level key, SIBLING of environment (not nested)
  app_store_connect: <key_name>            # must match the Team Settings key name
scripts:
  - name: Set up keychain to be used for code signing using Codemagic CLI 'keychain' command
    script: keychain initialize
  - name: Fetch signing files
    script: | 
      app-store-connect fetch-signing-files "$BUNDLE_ID" \
        --type IOS_APP_STORE \
        --create
  - name: Set up signing certificate
    script: keychain add-certificates
  - name: Set up code signing settings on Xcode project
    script: xcode-project use-profiles
```
- `--type`: `IOS_APP_STORE` | `IOS_APP_ADHOC` | `IOS_APP_DEVELOPMENT` | `IOS_IN_HOUSE`; `--create` lets
  Codemagic create a missing profile. Fetching by bundle id also pulls extension profiles.

### 2. Upload — certs/profiles uploaded to Codemagic, via the `ios_signing` block
You upload the `.p12` certificate and `.mobileprovision` profile in the Codemagic UI, then point the
`ios_signing` block at them — either by explicit **reference name**, or by letting Codemagic auto-match
on `distribution_type` + `bundle_identifier`. This is the only method that uses `ios_signing`.
```yaml
environment:
  ios_signing:
    provisioning_profiles:
      - profile: <profile_reference>       # name from the UI upload / get_team_signing
    certificates:
      - certificate: <certificate_reference>
scripts:
  - script: xcode-project use-profiles
```
- Auto-match alternative (instead of the explicit lists above):
  ```yaml
  environment:
    ios_signing:
      distribution_type: app_store         # app_store | ad_hoc | development | enterprise
      bundle_identifier: com.example.app   # must EXACTLY match the app's real bundle id
  ```
- Use `get_team_signing(team_id)` to find the uploaded `reference_name`s and confirm the profile's
  `bundle_id` / `distribution_type` matches the app.
- **Within `ios_signing`, the two forms are mutually exclusive**: don't combine
  `provisioning_profiles`/`certificates` (explicit) with `distribution_type`/`bundle_identifier`
  (auto-match) in the same block.

### 3. Envs — manual, base64 in environment variables (no ASC key needed)
You obtain and maintain the files yourself; store them base64-encoded as secrets in a group. Exact var
names Codemagic expects: `CM_CERTIFICATE` (base64 `.p12`), `CM_CERTIFICATE_PASSWORD` (if the cert is
password-protected), `CM_PROVISIONING_PROFILE` (base64 `.mobileprovision`).
```yaml
scripts:
  - name: Set up keychain to be used for code signing using Codemagic CLI 'keychain' command
    script: keychain initialize
  - name: Set up provisioning profiles from environment variables
    script: | 
        PROFILES_HOME="$HOME/Library/MobileDevice/Provisioning Profiles"
        mkdir -p "$PROFILES_HOME"
        PROFILE_PATH="$(mktemp "$PROFILES_HOME"/$(uuidgen).mobileprovision)"
        echo ${CM_PROVISIONING_PROFILE} | base64 --decode > "$PROFILE_PATH"
        echo "Saved provisioning profile $PROFILE_PATH"
  - name: Set up signing certificate
    script: | 
        echo $CM_CERTIFICATE | base64 --decode > /tmp/certificate.p12
        if [ -z ${CM_CERTIFICATE_PASSWORD+x} ]; then
            # when using a certificate that is not password-protected
            keychain add-certificates --certificate /tmp/certificate.p12
        else
            # when using a password-protected certificate
            keychain add-certificates --certificate /tmp/certificate.p12 --certificate-password $CM_CERTIFICATE_PASSWORD
        fi
  - name: Set up code signing settings on Xcode project
    script: xcode-project use-profiles
```
- No `ios_signing` block and no App Store Connect integration for this method. Put `CM_CERTIFICATE`,
  `CM_CERTIFICATE_PASSWORD`, `CM_PROVISIONING_PROFILE` in a secure env var group referenced by the workflow.

**Multiple provisioning profiles** (e.g. app extensions such as Notification Service): add each profile
as its own env var with a `CM_PROVISIONING_PROFILE_*` naming convention (e.g.
`CM_PROVISIONING_PROFILE_BASE`, `CM_PROVISIONING_PROFILE_NOTIFICATIONSERVICE`) in a group, then loop:
```yaml
environment:
  groups:
    - provisioning_profiles

# ...

scripts:
  - name: Set up Provisioning profiles from environment variables
    script: | 
      PROFILES_HOME="$HOME/Library/MobileDevice/Provisioning Profiles"
      mkdir -p "$PROFILES_HOME"
      for profile in "${!CM_PROVISIONING_PROFILE_@}"; do
        PROFILE_PATH="$(mktemp "$HOME/Library/MobileDevice/Provisioning Profiles"/ios_$(uuidgen).mobileprovision)"
        echo ${!profile} | base64 --decode > "$PROFILE_PATH"
        echo "Saved provisioning profile $PROFILE_PATH"
      done
```

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

### Unity (incl. VR / Oculus / Meta Quest)
Unity signs differently from the Gradle/Xcode defaults — the engine, not the build tool, applies signing:
- **License group (Secret):** `UNITY_EMAIL`, `UNITY_SERIAL`, `UNITY_PASSWORD`. (Build + license activate/
  return live in the `publishing` reference's Unity section.)
- **Android (and Oculus/Quest, which is a Unity Android build):** still reference the uploaded keystore via
  the `android_signing` block — Codemagic injects `CM_KEYSTORE_PATH` / `CM_KEYSTORE_PASSWORD` /
  `CM_KEY_ALIAS` / `CM_KEY_PASSWORD`. But Unity ignores Gradle's signing config, so your
  `Assets/Editor/Build.cs` must read those `CM_*` vars and set `PlayerSettings.Android.keystoreName` /
  `keystorePass` / `keyaliasName` / `keyaliasPass` programmatically. (Oculus distributes via the Oculus
  Platform Utility CLI with `OCULUS_APP_ID` + `OCULUS_APP_SECRET`/`OCULUS_USER_TOKEN`, not a `publishing:`
  block.)
- **iOS:** Unity exports an Xcode project; sign it with any of the three iOS methods above **after** the
  export (run `xcode-project use-profiles` on the exported project).

### Windows
- **MSIX / Microsoft Store:** package with the `msix` config; store creds in a group
  (`MS_STORE_ID`, `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`). See the publishing docs.

For most frameworks the iOS/Android/macOS blocks above are identical — only the **build command** differs:
- **React Native / Flutter / .NET MAUI → iOS or Android**: use the matching iOS/Android section as-is.

Confirm exact keys/flags against the docs and the official sample projects before committing.
