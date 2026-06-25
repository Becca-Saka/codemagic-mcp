# Instance types (build machines)

> Authoritative enum: https://codemagic.io/codemagic-schema.json (`InstanceType`) ·
> Pricing & plan availability: https://docs.codemagic.io/billing/pricing/

`instance_type` picks the build machine. The **family must match the platform** you build, and the
specific machine must be **available on the team's plan** — the schema validates the *name* but NOT plan
access, so a name the team's plan doesn't include will fail/queue at build time.

## Supported values

### macOS (required for iOS / macOS builds)
- `mac_mini_m2` — M2, 8-core / 8 GB. The safe default; the **only** machine on the free tier.
- `mac_mini_m4` — M4, 10-core / 16 GB. PAYG and the M4 annual plan.
- `mac_studio_m4_max` — M4 Max, 16-core / 32 GB. **M4 Max plan / Enterprise only.**

### Linux (Android / web / general)
- `linux_x2` — 8 vCPU / 32 GB. The standard Linux machine.
- `linux_x4` — 16 vCPU / 64 GB. **Enterprise / contact-sales (or M4 / M4 Max annual plans).**

### Windows
- `windows_x2` — 8 vCPU / 32 GB. The Windows machine.

### Do NOT use (removed — still in the schema enum but no longer supported)
- `mac_mini`, `mac_mini_m1`, `mac_pro` — deprecated; never emit these even though the schema still lists them.
- `linux` (legacy single-size) — prefer `linux_x2`.

## Choosing
- **iOS / macOS** → a `mac_*` instance (a combined workflow that includes any iOS/macOS build must use a
  mac instance). **Windows** → `windows_x2`. **Android / web / everything else** → a `linux_*` instance.
- Default to the broadly-available tier unless the user asked for more power: `mac_mini_m2`, `linux_x2`,
  `windows_x2`. These work on PAYG and the base annual plans.

## Plan availability (so you don't pick a machine the team can't run)
- **Free (individual):** `mac_mini_m2` only (500 min/mo); no free Linux/Windows minutes.
- **Pay-as-you-go:** `mac_mini_m2`, `mac_mini_m4`, `linux_x2`, `windows_x2` (per-minute).
- **Annual plans:** M2 plan → `mac_mini_m2` + `linux_x2` + `windows_x2`; M4 plan → `mac_mini_m4` +
  `linux_x4` + `windows_x2`; M4 Max plan → `mac_studio_m4_max` + `linux_x4` + `windows_x2`.
- **Enterprise:** all of the above, incl. `mac_studio_m4_max` and `linux_x4`.

When the team's plan is unknown, pick the default tier and tell the user the machine depends on their
plan (link the pricing page) rather than silently choosing an enterprise-only instance.
