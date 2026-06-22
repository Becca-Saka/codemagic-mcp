# Diagnose a Codemagic build failure

Find out why a Codemagic build failed and tell the user what went wrong and how to fix it.
You do the analysis yourself — these instructions tell you how to gather the evidence, what
to look for in it, and how to ground any Codemagic-specific claim. This is **diagnose and
recommend only**: explain the cause and the fix. If the fix is a repo change, you may apply it
through your own git tools after the user agrees — there is no Codemagic write tool here.

## Tools

- `list_team_builds(team_id?)` — recent builds for a team.
- `get_build_info(build_id)` — status, repo, commit, `config_source`, and `steps[]` (each with
  `step_id`, `name`, `status`, `log_url`).
- `get_build_step_logs(build_id, step_ids?)` — raw log text; defaults to the failed steps.

## Workflow

### 1. Identify the build
If a build id is already known from context, use it. Otherwise call `list_team_builds`, find the
failed build (most recent `failed` unless the user means another), and confirm with the user if it
is ambiguous.

### 2. Build overview — `get_build_info`
Read `status`, `steps[]` (find the `failed` one), `repo`, `commit`, `message`, and `config_source`.
- If `status` is `success` with no failed step, there is nothing to diagnose — say so and stop.
- `config_source` governs how you frame any fix:
  - `file` → a `codemagic.yaml` in the repo drives the build; config fixes are repo edits.
  - `ui` → a **Workflow Editor** app: there is **no `codemagic.yaml`**. The workflow, scripts,
    signing, and env live in the Codemagic UI; never tell the user to edit a yaml that does not exist.

### 3. Get the logs — `get_build_step_logs`
Call it for the failed step(s) (the default). Then:
- **No failed steps but the build failed:** the build-level `message` is the cause — some failures
  happen before any step runs (signing/config resolved at setup). Diagnose from `message`.
- **Silent signing failures:** a signing/archive step can fail with an empty or sparse log. The real
  error is usually in the **previous step**. If the failed step's name contains `sign`, `certificate`,
  `profile`, `keychain`, `archive`, or `export` and its log is thin, also fetch the prior step's log
  (pass its `step_id`) and read backwards until you find the actual error.

### 4. Classify — what to look for
Match the log against these signals to find the likely cause. Keep all distinct causes, most likely
first; treat them as hypotheses until the evidence confirms one.

| Category | Signals in the log | Where the fix lives |
| --- | --- | --- |
| script / environment | `exited with status code N`, `No such file or directory`, `command not found`, an undefined `$VAR` | repo script, or the Workflow Editor script for a `ui` app |
| compile | compiler errors from Dart/Swift/Kotlin/Gradle, `error:` from the toolchain | repo (source/config) |
| dependencies | pub/pod/gradle resolution conflicts, "version solving failed", "Could not find" | repo (dependency manifests) |
| signing | `code signing`, `provisioning profile`, `certificate`, `codesign`, "No signing certificate" | account / Apple Developer portal — often **not** the repo |
| config | `codemagic.yaml` parse errors, unknown keys, invalid `instance_type` | repo yaml (`file`) or Workflow Editor (`ui`) |
| integration / publishing | App Store Connect, Google Play, or webhook/publishing errors | account / external service |

### 5. Ground it — do not invent Codemagic specifics
- **Repo-side errors** (compile, dependencies, scripts) — diagnose straight from the log. No search needed.
- **Platform-side errors** (signing, `codemagic.yaml` syntax, integrations, Codemagic CLI tools) — do a
  **web search against the Codemagic sources below** before asserting syntax or behavior. Never write
  yaml keys or signing/CLI syntax from memory. If you cannot find the exact syntax, describe the fix
  conceptually instead of inventing fields.
- **Code signing especially** — signing errors are cryptic and recurring, and the same message has
  usually been reported and resolved before. Always **search the exact error line** across the sources
  below (knowledge base and discussions first, then docs and cli-tools) to find similar reported cases
  and their confirmed fix, rather than reasoning it out yourself. Quote the matching source's fix and
  link it; only fall back to a conceptual explanation if no similar case exists.

  - Docs — https://docs.codemagic.io/
  - Knowledge base — https://codemagic-knowledge-base.help.usepylon.com
  - `codemagic.yaml` schema — https://codemagic.io/codemagic-schema.json
  - API v3 schema — https://codemagic.io/api/v3/schema/openapi.json
  - CLI tools (`app-store-connect`, signing helpers) — https://github.com/codemagic-ci-cd/cli-tools
  - Sample projects (working configs by project type) — https://github.com/codemagic-ci-cd/codemagic-sample-projects
  - Community discussions (reported failures + fixes) — https://github.com/orgs/codemagic-ci-cd/discussions

### 6. Reply
- Lead with **what failed**, quoting the specific error line concisely — never paste the raw log.
- List the **likely causes** most-likely-first, each with a concrete fix, framed as hypotheses.
- Cite any Codemagic source you used as a markdown link.
- Match the fix to `config_source` — repo yaml/file edit for `file`, Workflow Editor steps for `ui`.
- Keep it conversational and short: no markdown headings, no walls of text, no raw log dumps.
- Suggest contacting Codemagic support only for genuine account/billing/infrastructure issues the user
  cannot self-fix, or when you have no actionable resolution.
