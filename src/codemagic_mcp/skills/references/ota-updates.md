# Over-the-air (OTA) updates — Shorebird (Flutter) & CodePush (React Native)

OTA lets you ship code patches without a new store submission. Pick the tool by framework.

## Shorebird — Flutter
> Docs: https://docs.shorebird.dev/code-push/ci/codemagic/

Two modes: **release** (create a new Shorebird release) and **patch** (OTA-update an existing release).

- Store `SHOREBIRD_TOKEN` in an env var group (e.g. `shorebird`) and reference it in every Shorebird
  workflow alongside your signing group.
- Install Shorebird as the first script step, then run release/patch instead of `flutter build`:
  ```yaml
  scripts:
    - name: Install Shorebird
      script: |
        curl --proto '=https' --tlsv1.2 \
          https://raw.githubusercontent.com/shorebirdtech/install/main/install.sh -sSf | bash
        echo PATH="$HOME/.shorebird/bin:$PATH" >> $CM_ENV
    - name: Shorebird release android
      script: shorebird release android --flutter-version="$FLUTTER_VERSION"
  ```
- **Patch** mode: `shorebird patch android --release-version=1.0.0+1`; pass the release version as a
  pipeline variable so it can be set per run. The `--release-version` must match an existing release.

## CodePush — React Native
> Verify against current docs first.

React Native OTA was historically Microsoft App Center CodePush, which is **retired/migrating** — do
not write App Center CodePush steps from memory. Check the docs and sample projects for the currently
recommended RN OTA path (e.g. a self-hosted CodePush server or a vendor alternative) before configuring
it, and tell the user which secrets/integration it needs.

Confirm exact CLI flags and secret names against the docs and the official sample projects.
