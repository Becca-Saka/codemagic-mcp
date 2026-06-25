# Publishing and notifications

> Docs: https://docs.codemagic.io/yaml-publishing/

All under the workflow's `publishing:` key. Reference secrets via env var groups — never inline them.

## Email
```yaml
publishing:
  email:
    recipients: [user@example.com]
    notify: {success: true, failure: true}
```

## Slack
```yaml
publishing:
  slack:
    channel: "#builds"
    notify_on_build_start: false
    notify: {success: true, failure: true}
```
Requires a Slack integration configured in the Codemagic UI.

## Google Play
```yaml
publishing:
  google_play:
    credentials: $GOOGLE_PLAY_SERVICE_ACCOUNT_CREDENTIALS
    track: internal            # internal | alpha | beta | production
    submit_as_draft: false
```
Needs a Play service account JSON (Release Manager) in an env var group.

## App Store Connect
Preferred — Codemagic integration:
```yaml
integrations:
  app_store_connect: codemagic
publishing:
  app_store_connect:
    auth: integration
    submit_to_testflight: true
    submit_to_app_store: false
```
Or via env vars: `api_key: $APP_STORE_CONNECT_PRIVATE_KEY`, `key_id`, `issuer_id`.

## Firebase App Distribution
```yaml
publishing:
  firebase:
    firebase_token: $FIREBASE_TOKEN
    android: {app_id: $FIREBASE_ANDROID_APP_ID, groups: [qa-team], artifact_type: apk}
    ios: {app_id: $FIREBASE_IOS_APP_ID, groups: [qa-team]}
```

## Custom notifications — Telegram, Teams, Google Chat, Discord, generic webhook
Codemagic has built-in blocks only for **email** and **Slack**. For any other channel there is no
`publishing:` key — you send the message yourself with a script that POSTs to that service's
webhook/bot API. Don't invent the exact payload from memory: look up the service's incoming-webhook
format (and Codemagic's per-service examples at https://docs.codemagic.io/yaml-notification/, which
covers Telegram, Discord, etc.) and adapt it. The **steps** are always the same:

1. **Store the webhook/token as a secure env var** in a group (e.g. `TELEGRAM_BOT_TOKEN` +
   `TELEGRAM_CHAT_ID`, `TEAMS_WEBHOOK_URL`, `GOOGLE_CHAT_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`). Never
   inline it. Add it to the workflow's `environment: groups:` and to the runnable-setup checklist.
2. **Make build status available to the notification step.** A `publishing: scripts:` step runs after
   the build/publish phase. To know whether the build itself passed, write a marker as the **last build
   step**, then in the notification step combine it with the publishing-action status from the builds API
   (`GET https://api.codemagic.io/builds/$CM_BUILD_ID`, header `x-auth-token: $CODEMAGIC_API_TOKEN`):
```yaml
scripts:
  # ... build steps ...
  - name: Mark build successful
    script: touch ~/SUCCESS          # last build step; absent if an earlier step failed
```
3. **Send the message from a `publishing: scripts:` step** (publishing scripts run even when the build
   fails, so the notification fires for failures too). Determine the status, then POST:
```yaml
publishing:
  scripts:
    - name: Notify Telegram
      script: |
        if [ -f ~/SUCCESS ]; then
          STATUS=$(curl -s \
            -H "Content-Type: application/json" \
            -H "x-auth-token: $CODEMAGIC_API_TOKEN" \
            --request GET "https://api.codemagic.io/builds/$CM_BUILD_ID" | \
            jq -r '.build.buildActions[]? | select(.type=="publishing") | .status')
          if [ "$STATUS" = "success" ]; then BUILD_STATUS="✅ success"; else BUILD_STATUS="⚠️ publishing failed"; fi
        else
          BUILD_STATUS="❌ build failed"
        fi
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
          -d chat_id="$TELEGRAM_CHAT_ID" \
          -d text="Build $CM_BUILD_ID for $CM_PROJECT_ID: $BUILD_STATUS"
```
Swap the `curl` target + payload for the chosen service (Teams/Google Chat/Discord take a JSON body to a
webhook URL). Keep it as its own named step (don't fold it into the build steps).

## Windows — Microsoft Store (Partner Center)
```yaml
publishing:
  partner_center:
    store_id: $MS_STORE_ID
    tenant_id: $MS_TENANT_ID
    client_id: $MS_CLIENT_ID
    client_secret: $MS_CLIENT_SECRET
```
Store the four `MS_*` values in a secure group.

## Unity — license + build + Steam
> Docs: https://docs.codemagic.io/yaml-quick-start/building-a-unity-app/ ·
> https://docs.codemagic.io/yaml-publishing/steam/

Unity isn't Windows-specific — the same project builds Android / iOS / macOS / Windows. Three pieces:
- **License (env group, Secure):** `UNITY_EMAIL`, `UNITY_SERIAL`, `UNITY_PASSWORD`. Activate at the start
  of `scripts` with `Unity -batchmode -quit -logFile - -serial $UNITY_SERIAL -username $UNITY_EMAIL
  -password $UNITY_PASSWORD`, and **return the license in a `publishing:` script** so it's released even
  on failure: `Unity -batchmode -quit -returnlicense -username $UNITY_EMAIL -password $UNITY_PASSWORD`.
- **Unity version:** pin it on macOS with `environment: unity: <version>` (e.g. `2021.3.6f1`) — Codemagic
  installs it and sets `$UNITY_HOME`. For other platforms / extra modules, install via the Unity Hub CLI
  (`Unity Hub -- --headless install --version $V --changeset $CS` then `install-modules … -m ios android`),
  reading the version from `ProjectSettings/ProjectVersion.txt`.
- **Build:** add static build methods in `Assets/Editor/Build.cs` (e.g. `BuildAndroid`/`BuildIos`/
  `BuildMac`/`BuildWindows`) and run `Unity -batchmode -quit -projectPath . -executeMethod
  Build.BuildAndroid -nographics`. Android emits an AAB; iOS exports an Xcode project you then build with
  `xcode-project build-ipa`; Windows needs a **windows** instance.
- **Distribution:** mobile/desktop targets use the normal blocks above (Google Play, App Store Connect,
  email, …). For **Steam** (Codemagic's Steam guide covers Unity), there is no `publishing:` block —
  deploy with a script.

### Steam (script-based)
- Secrets in a secure group: `STEAM_USERNAME`, `STEAM_PASSWORD`, `SSFN_FILE_NAME`, `SSFN_FILE` (base64
  sentry file), `CONFIG_FILE` (base64 `config.vdf`). The SSFN + config sentry files let `steamcmd` skip
  Steam Guard.
- Commit the Steam build scripts: `steam/app_build.vdf` (AppID / DepotID / branch / content root) and
  `steam/depot_build.vdf` (local-file → depot mapping).
- Decode the sentry/config files into Steam's dir, then run:
  `~/Steam/steamcmd.sh +login $STEAM_USERNAME $STEAM_PASSWORD +run_app_build <repo>/steam/app_build.vdf +quit`.

## Web & script-based targets (no `publishing:` block — deploy from a script)
These have no built-in `publishing:` key; add a deploy **script** step (store creds as secure env vars,
add them to the runnable-setup checklist), and confirm the exact CLI against the docs:
- **Firebase Hosting** — `firebase deploy --only hosting --token $FIREBASE_TOKEN` (or a service account).
- **Cloudflare Pages** — `wrangler pages deploy <dir>` with `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`.
- **GitHub Releases** — `gh release create` / the Codemagic `github` CLI with `GITHUB_TOKEN`.
- **Codemagic static pages** — host the web build artifact on Codemagic; no extra credentials.
- **Huawei AppGallery** — Fastlane AppGallery plugin with `HUAWEI_CLIENT_ID` / `HUAWEI_CLIENT_SECRET` /
  `HUAWEI_APP_ID`.

## Others
Also supported: Amazon S3, Google Cloud Storage, pub.dev. Confirm each target's exact keys against its
docs page.
