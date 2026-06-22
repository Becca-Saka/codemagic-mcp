# Create a codemagic.yaml

Produce a working `codemagic.yaml` for the user's project. You write it yourself — these
instructions tell you what to gather, how to ground the structure so you don't invent keys, and how
to verify it. Always validate before presenting. This writes a file only; commit it through your own
git after the user agrees — there is no Codemagic write tool here.

## Tool

- `validate_codemagic_yaml(yaml_content)` — checks the full yaml against the official Codemagic schema
  and returns `{valid, errors[]}`. Run it before showing anything; fix and re-run until valid.

## Workflow

### 1. Know the project
You are working in the user's project. **Detect first, ask last** — read the repo to determine
everything that's discoverable, and only ask the user for genuine decisions and secrets you cannot
infer. Never ask for something the project files already tell you.

**Detect from the repo (do not ask if found):**
- **Project type** — flutter (`pubspec.yaml`), react-native (`package.json` + native folders), unity,
  cordova/ionic (`config.xml`/`ionic.config.json`), kotlin-multiplatform, dotnet-maui (`.csproj`), or
  native Android/iOS.
- **Platforms** — from which native folders exist (`android/`, `ios/`, `macos/`, `web/`, `windows/`).
- **Identifiers** — Android package name from `android/app/build.gradle(.kts)`; iOS/macOS bundle id and
  Xcode scheme from `ios/Runner.xcodeproj/project.pbxproj`, `*.xcscheme`, or `Info.plist`.
- **Default branch / monorepo path** — from git and the project layout.

Confirm a detected value only if it's ambiguous (e.g. multiple schemes or flavors); otherwise use it.

**Ask the user (decisions/secrets you can't infer):**
- **Signing** — iOS/macOS: `automatic` (App Store Connect integration), `codemagic-managed` (certs
  uploaded in the Codemagic UI), `manual` (env var groups), or none. Android: keystore (env var group)
  or none. If you know the team id, call `get_team_signing(team_id)` first: when a matching, valid
  profile/certificate is already uploaded (check its `bundle_id` and `distribution_type`), reference it
  by `reference_name` and just confirm the method — don't ask the user to set up signing from scratch.
  Before writing any signing block, pull `codemagic_yaml_reference("code-signing")` — signing has strict
  rules (e.g. never mix the `ios_signing` block with the App Store Connect integration method).
- **Distribution** — App Store Connect / Google Play (which track), Firebase App Distribution, email
  artifact, or none.
- **Triggering** — events (push, pull_request, tag, or manual only) and which branches.
- **Build versioning** — auto-version store uploads, and the strategy.
- **Notifications** — email addresses, Slack channel.
- **Workflows** — one combined workflow, or one per target.

Batch the questions you do need into one concise round — don't interrogate field by field.

### 2. Ground the structure — do not invent keys
- The authoritative shape is the schema — **only use keys it defines**:
  https://codemagic.io/codemagic-schema.json
- For working patterns by project type and scenario (signing, publishing, versioning), **base your yaml
  on a matching official sample** rather than writing blocks from memory:
  https://github.com/codemagic-ci-cd/codemagic-sample-projects — find the closest project type +
  signing/publishing combination, copy its structure, then adapt names and identifiers.
- For exact field meanings, consult the docs: https://docs.codemagic.io/

### 3. Write the yaml
- One workflow per build target unless the user wants a single combined one. Give each a clear `name`
  and an appropriate `instance_type`.
- Per workflow set `environment` (toolchain versions, environment variable `groups`, `vars`), `scripts`
  (build steps), `artifacts`, and `publishing`.
- **Code signing** — place it per the chosen method: an App Store Connect integration reference, an
  environment variable group holding the keystore/cert material, or codemagic-managed signing.
  Reference secrets through environment variable **groups** — never inline a secret value.
- **Build versioning** — apply the chosen strategy for store builds.
- **Triggering** — set `triggering.events` and the branch patterns.
- Reference env-group secrets, never inline them.

**Pull a reference before writing each non-trivial area.** Call `codemagic_yaml_reference(topic)` for
the Codemagic-specific patterns rather than working from memory:
- `definitions-and-anchors` — dedup shared blocks across multiple workflows.
- `build-versioning` — auto build-number strategies (counters, store-latest+1, manual).
- `environment-and-cache` — toolchain versions, env var groups, cache paths.
- `code-signing` — iOS/macOS/Android signing methods and their do's & don'ts (read before any signing block).
- `publishing` — App Store Connect, Google Play, Firebase, email/Slack.
- `triggering` — events, branch/tag patterns, cancel-previous.
- `ota-updates` — Shorebird (Flutter) and CodePush (React Native) over-the-air patches.

### 4. Validate — always
- Call `validate_codemagic_yaml` on the full content.
- For each error, fix it using the `path` + `message`, then re-validate. Repeat until `valid: true`.
- Never present a yaml you have not validated.

### 5. Present
- Show the final, validated yaml.
- Call out every placeholder the user must fill — environment variable group names, integration names,
  identifiers — and where to set them in Codemagic (Team/App settings → environment variables /
  integrations).
- Keep it conversational: briefly explain the key choices, no walls of text.
