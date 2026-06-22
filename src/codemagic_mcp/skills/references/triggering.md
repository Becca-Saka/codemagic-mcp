# Triggering

> Docs: https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/#triggering

```yaml
triggering:
  events:
    - push
    - pull_request
    - tag
  branch_patterns:
    - pattern: 'main'
      include: true
      source: true          # apply to the source branch of pull requests
    - pattern: 'develop'
      include: true
  tag_patterns:
    - pattern: 'v*'
      include: true
  cancel_previous_builds: true
```

- Events: `push`, `pull_request`, `pull_request_labeled`, `tag`.
- `cancel_previous_builds: true` cancels queued builds for the same branch on a new commit.
- `triggering` usually differs per workflow — don't share it via an anchor.
- A webhook must be configured for the repository (Codemagic does this when the app is connected).
