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

## Others
Also supported: GitHub releases, Microsoft Store, Huawei AppGallery, Amazon S3, Google Cloud Storage,
Cloudflare Pages, pub.dev, Steam. Confirm each target's exact keys against its docs page.
