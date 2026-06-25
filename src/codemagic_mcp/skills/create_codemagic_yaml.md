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
- **Flavors / build variants — you MUST actively check, never assume "none".** Variants change the build
  command and identifiers and usually mean one workflow each, so missing them produces a wrong config.
  Run the actual detection before writing anything — don't just read about it:
  - Android: `grep -n "productFlavors\|flavorDimensions" android/app/build.gradle*` — any match ⇒ flavors.
  - iOS/macOS: `ls ios/*.xcodeproj/xcshareddata/xcschemes/ macos/*.xcodeproj/xcshareddata/xcschemes/`
    — more than the one default scheme ⇒ variants.
  - Flutter: also `grep -rn "\-\-flavor" .` and check for `flutter_flavorizr` in `pubspec.yaml` and
    `lib/main_*.dart` / `lib/flavors.dart`.
  State what you found ("flavors: dev, prod" or "no flavors detected") so it's explicit. If variants
  exist, ask the user which to build and make a workflow per chosen flavor; pull
  `codemagic_yaml_reference("flavors")` for the other project types and the per-flavor command/signing
  details. Only treat the project as single-flavor after the checks above come back empty.
- **Default branch / monorepo path** — from git and the project layout.

Confirm a detected value only if it's ambiguous (e.g. multiple schemes/flavors and it's unclear which to
build, or which bundle id / package name pairs with each); otherwise use it. When several flavors exist,
ask which to build (one, several, or all) — see the `flavors` reference.

**Look up real values from the account before asking (and never guess them):**
Several fields must be exact strings that exist in the user's Codemagic account — an integration
name, a variable group name, a signing `reference_name`. Do not invent these and do not leave a
`<placeholder>` for them when a tool can return the real value:
- `get_team_integrations(team_id)` — real App Store Connect / Partner Center **integration names**
  and tester group names (for `integrations:` / `app_store_connect:` and tester distribution).
- `list_variable_groups(app_id | team_id)` — real environment variable **group names** (and the keys
  inside them) to reference for secrets.
- `get_team_signing(team_id)` — uploaded certs/profiles to reference by `reference_name`.

If a needed value isn't found by a tool, **ask the user for it** — don't substitute a placeholder.

**You can also create the env setup, not just reference it.** If the yaml needs a variable group that
doesn't exist yet, offer to create it and populate it instead of sending the user to the UI:
- `create_variable_group(name, app_id | team_id)` — make the group the yaml references.
- `add_environment_variables(group_id, {NAME: value}, secure=True)` — add the variables (values are
  sent to Codemagic, never echoed). Ask the user for the secret values; add them as `secure`.
Only do this with the user's go-ahead (it writes to their account), and prefer an existing group when
`list_variable_groups` already returns a suitable one.

**Ask the user (decisions/secrets you can't infer or look up):**
- **Signing — ask iOS/macOS and Android as SEPARATE questions** (never merge them into one "signing"
  question); ask each only for the platforms the app actually targets.
  - **iOS/macOS signing** — three methods (pick one), or none: **ASC** (automatic — App Store Connect
    API integration fetches certs/profiles), **upload** (certs/profiles uploaded to Codemagic, referenced
    by name), or **envs** (base64 `.p12`/profile in a secure env var group).
  - **Android signing** — keystore (env var group / uploaded), or none.
  Call `get_team_signing(team_id)` first: when a matching, valid profile/certificate/keystore is already
  uploaded (check its `bundle_id` and `distribution_type`), prefer the **upload** method and reference it
  by `reference_name` — don't ask the user to set up signing from scratch.
  Before writing any signing block, pull `codemagic_yaml_reference("code-signing")` — signing has strict
  rules (e.g. never mix the `ios_signing` block with the App Store Connect integration method).
- **Distribution** — App Store Connect / Google Play (which track), Firebase App Distribution, email
  artifact, or none. For App Store Connect, confirm the exact **integration name** from
  `get_team_integrations`; if missing, ask — never invent it.
- **Triggering** — events (push, pull_request, tag, or manual only) and which branches. If they want
  tag builds, **ask for the actual tag pattern** (e.g. `v*`, `release-*`) — don't default to a guess.
- **Build versioning** — auto-version store uploads, and the strategy.
- **Notifications** — email, Slack, or another channel (Telegram, Microsoft Teams, Google Chat, Discord,
  a generic webhook). Email and Slack have built-in `publishing:` blocks; for any other channel there is
  no built-in block — you send it with a custom `publishing: scripts:` step. When the user picks one of
  these, pull `codemagic_yaml_reference("publishing")` and follow the custom-notification steps (store the
  webhook/token as a secure env var, mark build status, POST from a publishing script) — don't invent the
  payload from memory.
- **Workflows / flavors** — one combined workflow, or one per target; and if the flavor check above found
  variants, which flavor(s) to build. Include this in the same question round.

Ask these in one round, but as **separate, distinct questions, each with its own concrete options**
(flavor, iOS signing, Android signing, distribution, triggering, etc. are individual questions). "One
round" means one batch of questions, not one summarized question.

**Each question's options must be the literal enumerated choices for that ONE decision** — exactly the
options listed above (e.g. iOS signing → `ASC` / `upload` / `envs` / `none`; Android signing → `keystore`
/ `none`; distribution → `App Store Connect` / `Google Play` / `Firebase` / `email` / `none`). Do NOT:
- invent **bundled "scenario" presets** that fold several decisions into one option (e.g. "Full signing +
  store upload", "None / unsigned", "Email artifacts only") — these hide the real choices and the user
  can't pick a method;
- **merge signing with distribution**, or **merge iOS with Android**, into a single question;
- paraphrase or summarize the choices away.
Present each decision on its own with its real options so the user picks each one explicitly.

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
- **Scripts — one logical action per step, each with a `name`.** Split the build into separate named
  `scripts` steps (e.g. install dependencies, set up signing, build, test) instead of cramming several
  commands into one `script: |` block. Separate steps give readable per-step logs and pinpoint which
  stage failed. Keep multiple commands in a single step only when they're inherently one unit (a loop,
  or a sequence that shares local shell state). This applies to every section, signing included.
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
- `flavors` — detecting build variants per project type and writing one workflow per flavor.

### 4. Validate — always
- Call `validate_codemagic_yaml` on the full content.
- For each error, fix it using the `path` + `message`, then re-validate. Repeat until `valid: true`.
- Never present a yaml you have not validated.

### 5. Present
- Show the final, validated yaml.
- It should contain **real values, not placeholders** — by this point integration names, group names,
  signing reference names, identifiers, and tag patterns should be the actual ones you looked up via
  tools or got from the user. A `<placeholder>` is only acceptable for a value no tool exposes and the
  user genuinely hasn't decided yet; if any remain, list each one and where to set it in Codemagic
  (Team/App settings → environment variables / integrations), and offer to fill it once they provide it.
- Keep it conversational: briefly explain the key choices, no walls of text.

**Then help the user make it actually runnable** — don't stop at the file. Walk the gaps the yaml
implies and offer to close each one (only act on a yes; these write to their account):
- **App not on Codemagic yet** — if `list_applications` didn't show this repo, tell the user and offer
  to add it with `add_application` (confirm the repo URL and which team).
- **Missing variable groups / env vars** — for any group the yaml references that doesn't exist (or is
  missing keys), offer to create it (`create_variable_group`) and upload the values. First **derive the
  exact keys the build needs from the yaml you wrote** (each `groups:` it references and each
  publishing/signing block implies specific keys — e.g. `google_play` ⇒ `GCLOUD_SERVICE_ACCOUNT_CREDENTIALS`,
  the `envs` signing method ⇒ `CM_KEYSTORE*` / `CM_CERTIFICATE*`) and list them so the user knows what to
  provide.
- **Upload secrets via a file, never via chat.** Use `add_environment_variables(group_id, file_path=...)`:
  ask the user to put the keys in a local dotenv file and give you its **path** — the server reads it; you
  must NOT open, cat, or Read the file. File format, one `KEY=value` per line:
  - `KEY=value` — a literal value (fine for non-secret config).
  - `KEY=@path` — store the file's **raw text** (service-account JSON, `.p8` key, PEM).
  - `KEY=@base64:path` — **base64-encode** the file (keystore, `.p12`, `.mobileprovision`); relative paths
    resolve against the dotenv file. This is exactly what Codemagic expects for binary signing material.
  Clearly non-secret values you already know can instead go inline via `variables={...}`.
- After uploading, confirm which **keys** were set (never the values) and that they match what the yaml
  references, then offer to delete the secrets file — so committing the yaml yields a green build.
