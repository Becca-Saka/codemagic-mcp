# Migrate a Workflow Editor (UI) app to codemagic.yaml

Convert a Codemagic app configured in the **Workflow Editor** (`config_source: ui`) into an equivalent
`codemagic.yaml`. You read the app's existing UI config and translate it field by field, then follow the
`create_codemagic_yaml` playbook to ground, validate, and present. Writes a file only — commit it via
your own git after the user agrees.

## Tools
- `get_application(app_id)` — the app's redacted UI config: workflows, scripts, build settings, signing,
  publishers, and env var names/groups (values are redacted).
- `get_team_signing(team_id)` — uploaded signing identities, to resolve signing references.
- `validate_codemagic_yaml(yaml_content)` — schema check.

## Workflow

### 1. Read the app config
Call `get_application(app_id)`.
- If `config_source` is not `ui`, there is no Workflow Editor config to migrate (the app is already
  file-based / uses a codemagic.yaml). Say so; if they want a fresh config, use `create_codemagic_yaml`.
- Note `team_id`, `project_type`, `repo`, and the `workflows` list.

### 2. Scope
If the app has more than one workflow, ask which to migrate (all, or specific ones). A single workflow →
migrate it directly.

### 3. Translate each UI workflow → a yaml workflow
Map the existing config; do not invent or add settings that aren't there:
- `name`, `instance_type` → the workflow's `name` and `instance_type`.
- `branch_patterns` / `tag_patterns` + `build_settings` (`automaticBuilds`, `buildOnPrUpdate`,
  `tagBuilds`, `cancelPreviousBuilds`) → `triggering` (events + branch/tag patterns +
  `cancel_previous_builds`).
- `scripts` (the `customScripts` map: `postClone`, `preBuild`, `postBuild`, `preTest`, `postTest`,
  `prePublish`, `postPublish`) → the `scripts` list **in that order**, preserving each script's content.
  Use `build_settings.target` / `projectFile` / `flutterMode` to form the build command.
- **Flavor / scheme** — if `build_settings` carries a flavor or Xcode scheme (or the app has a workflow
  per variant), preserve it in the build command and keep one workflow per flavor. Pull
  `codemagic_yaml_reference("flavors")` if you need the per-project-type specifics.
- `code_signing` → the signing setup. For `android.enabled`, wire a keystore via an env var group; for
  `ios.bundle_id`, set up iOS signing. Call `get_team_signing(team_id)` to find the matching uploaded
  profile/certificate and reference it by `reference_name`.
- `publishers` → `publishing`: `email.recipients` → email; `googlePlay` (track) → `google_play`;
  `appStoreConnect` → `app_store_connect`; `firebase` → `firebase`. Credentials are secrets — reference
  env var groups, never values. For the App Store Connect / Partner Center **integration name**, take the
  real name from `get_team_integrations(team_id)` — don't invent it or leave a placeholder; if it isn't
  found, ask the user which integration to use.
- `environment_variables` (names/groups only) → `environment.groups` (and `vars` for clearly non-secret
  values). The actual secret values are **not** migrated. Offer to recreate the groups and add the
  values for the user (`create_variable_group` + `add_environment_variables`, asking them for each secret
  value) instead of leaving it all manual — only with their go-ahead, since it writes to the account.

### 4. Ground, write, validate — follow `create_codemagic_yaml`
From here, follow the `create_codemagic_yaml` playbook: pull `codemagic_yaml_reference(topic)` for each
area involved (e.g. `triggering`, `publishing`, `environment-and-cache`, and
`definitions-and-anchors` when there are multiple workflows), write the yaml grounded in the schema and
sample projects, and **always** run `validate_codemagic_yaml`, fixing until valid.

### 5. Present
- Show the validated yaml.
- The yaml should carry **real** integration names, group names, signing reference names, identifiers,
  and tag/branch patterns — looked up via tools or confirmed with the user, not placeholders.
- List what the user must still do: set the secret env var **values** (not migrated) — or offer to add
  them now via `create_variable_group` / `add_environment_variables` — and switch the app to use the
  `codemagic.yaml` once it's committed.
- Flag any UI setting that has no direct yaml equivalent rather than silently dropping it.
