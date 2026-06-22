# Environment and cache

> Docs: https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/

## Environment
```yaml
environment:
  groups:
    - keystore_credentials      # secret env var groups configured in Codemagic
    - google_play
  vars:
    PACKAGE_NAME: "com.example.app"   # non-secret public values only
  flutter: stable
  xcode: latest
  cocoapods: default
  java: 17
  node: 18.17.0
  ndk: r25c
```
**Groups rule:** any environment variable configured in Codemagic app/team settings **must** be
referenced under `groups`. Inline `vars` are for non-secret public values only — never inline a secret.

## Cache
Each workflow has its own cache. Add a `cache` block with the paths your toolchain reuses:
```yaml
cache:
  cache_paths:
    - ~/.pub-cache
    - ~/.gradle/caches
    - ~/Library/Caches/CocoaPods
    - ./node_modules
```
Cache only stable dependency dirs — not build output. Pick the paths that match the project type.
