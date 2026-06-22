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

## Others
Also supported: GitHub releases, Microsoft Store, Huawei AppGallery, Amazon S3, Google Cloud Storage,
Cloudflare Pages, pub.dev, Steam. Confirm each target's exact keys against its docs page.
