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
- **Signing** — iOS/macOS has three methods (pick one): **ASC** (automatic — App Store Connect API
  integration fetches certs/profiles), **upload** (certs/profiles uploaded to Codemagic, referenced by
  name), or **envs** (base64 `.p12`/profile in a secure env var group); or none. Android: keystore
  (env var group / uploaded) or none. Call `get_team_signing(team_id)` first: when a matching, valid
  profile/certificate is already uploaded (check its `bundle_id` and `distribution_type`), prefer the
  **upload** method and reference it by `reference_name` — don't ask the user to set up signing from scratch.
  Before writing any signing block, pull `codemagic_yaml_reference("code-signing")` — signing has strict
  rules (e.g. never mix the `ios_signing` block with the App Store Connect integration method).
- **Distribution** — App Store Connect / Google Play (which track), Firebase App Distribution, email
  artifact, or none. For App Store Connect, confirm the exact **integration name** from
  `get_team_integrations`; if missing, ask — never invent it.
- **Triggering** — events (push, pull_request, tag, or manual only) and which branches. If they want
  tag builds, **ask for the actual tag pattern** (e.g. `v*`, `release-*`) — don't default to a guess.
- **Build versioning** — auto-version store uploads, and the strategy.
- **Notifications** — email addresses, Slack channel.
- **Workflows / flavors** — one combined workflow, or one per target; and if the flavor check above found
  variants, which flavor(s) to build. Include this in the same question round.

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
- For any variable **group** the yaml references that doesn't exist yet, offer to create it and add the
  variables now (`create_variable_group` + `add_environment_variables`) rather than only pointing at the
  UI — so the build is runnable when they commit.
- Keep it conversational: briefly explain the key choices, no walls of text.
