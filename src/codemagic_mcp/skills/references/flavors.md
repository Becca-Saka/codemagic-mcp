# Flavors & build variants

> Docs: https://docs.codemagic.io/yaml-running-builds/building-flavored-projects/

A "flavor" is a build variant of the same codebase — different bundle id / package name, assets,
config, or backend per variant (e.g. `dev`, `staging`, `production`). Variants change the **build
command**, the **identifiers**, and usually the **signing/publishing** target, so the rule is **one
workflow per variant you ship**. Detect them, confirm which to build, then write a workflow each.

## Where each project type keeps its variants

| Project type | What the variants are called | Detect from |
| --- | --- | --- |
| Flutter | flavors | Android `productFlavors` + iOS schemes (below); `--flavor` in scripts; `flutter_flavorizr` in `pubspec.yaml`; `lib/main_<flavor>.dart` / `lib/flavors.dart` |
| Android (native / RN / KMP) | product flavors (+ build types) | `productFlavors { … }` and `flavorDimensions` in `android/app/build.gradle(.kts)` |
| iOS / macOS (native / RN / Flutter) | schemes (+ configurations) | shared `*.xcscheme` files in `*.xcodeproj/xcshareddata/xcschemes/` (and `*.xcworkspace`); build configs in `project.pbxproj` |
| React Native | Android product flavors + iOS schemes | as the Android/iOS rows above |
| Ionic / Cordova / Capacitor | no own concept — native variants | the generated `android/` flavors and `ios/` schemes; plus JS env configs (`.env.<flavor>`, `environments/`) |
| Unity | build targets / platforms, **build profiles**, scripting-define symbols | `ProjectSettings/`, `.buildprofile` assets, per-target define symbols |
| .NET MAUI | build configurations + target frameworks | `<Configurations>` / `<TargetFrameworks>` in the `.csproj` |
| Kotlin Multiplatform | Android flavors + iOS schemes | as the Android/iOS rows |

A project with no `productFlavors` and a single shared scheme has **no flavors** — write one workflow.
Multiple shared schemes or any `productFlavors` block ⇒ variants exist; confirm before assuming.

## Writing flavored workflows

- **One workflow per flavor** the user wants to ship. Name them clearly (`android-staging`,
  `ios-production`). Don't fold multiple flavors into one workflow.
- Pass the flavor through the build command per project type:
  - Flutter — `flutter build appbundle --flavor staging -t lib/main_staging.dart`
    (and `flutter build ipa --flavor staging …`).
  - Android — build the variant task, e.g. `./gradlew assembleStagingRelease` /
    `bundleStagingRelease`.
  - iOS/macOS — build/archive the matching **scheme** (`xcode-project build-ipa --scheme Staging …`).
  - .NET MAUI — `-c Release` with the chosen configuration / `-f` target framework.
  - Unity — the target/build-profile in the Unity build script.
- **Identifiers differ per flavor** — set the right bundle id / package name for each (detect each
  variant's id; don't reuse one across flavors).
- **Signing & publishing are per flavor** — each flavor usually has its own provisioning profile /
  keystore alias and its own store target/track. Reference the right signing material and
  `publishing` block per workflow. Pull `code-signing` and `publishing` references when writing them.
- **Dedup the shared parts** — toolchain versions, cache, common scripts repeat across flavor
  workflows; factor them with anchors. Pull `definitions-and-anchors`.
- Per-flavor secrets (different Firebase config, API keys) belong in **separate variable groups** —
  reference the group that matches the flavor.
