# Definitions and anchors (dedup)

Declare reusable blocks under the top-level `definitions:` key and reference them in workflows. Extract
a block only when **2+ workflows share it (near-)identically**; inline anything unique to one workflow.

## Referencing
- List / scalar — direct alias: `artifacts: *common_artifacts`.
- Mapping — merge key, then override what differs:
  ```yaml
  definitions:
    environment: &base_env
      flutter: stable
      xcode: latest
  workflows:
    ios:
      environment:
        <<: *base_env
        xcode: "15.4"        # override just this; explicit keys win over merged
        groups: [ios_signing]
  ```
  A workflow may merge multiple anchors (`<<: *base_env` then `<<: *signing_vars`); a later merge wins on conflict.

## Good to anchor
Shared `environment` versions, env `groups`, artifact globs, `publishing` (email/Slack), `cache_paths`,
and helper scripts that are truly identical (`flutter pub get`, lint, test).

## Do NOT anchor
- Platform-specific build commands — Android `flutter build appbundle` vs iOS `flutter build ipa` are
  not interchangeable; keep each in its own workflow's `scripts`.
- `triggering` (usually differs per workflow), `instance_type`/`max_build_duration` (unless identical
  everywhere), and any block unique to one workflow.
