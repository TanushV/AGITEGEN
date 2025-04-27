```markdown
# AiderGen

*A one-command generator that turns an idea into a working cross-platform app.*

AiderGen captures requirements with **Gemini 2.5 Pro**, writes code through **Aider AI**, fixes failing tests with **OpenAI o3**, scaffolds React-Native / Flutter / Next.js projects, wires optional Supabase or Firebase stubs, embeds the relevant backend docs for RAG, and ships a full CI/CD matrix—Detox E2E, Flutter integration tests, and remote iOS builds that fit inside GitHub’s free tier.

---

## Table of Contents
1. [Features](#features)  
2. [Repository Map](#repository-map)  
3. [Prerequisites](#prerequisites)  
4. [Installation](#installation)  
5. [Quick Start](#quick-start)  
6. [Architecture](#architecture)  
7. [Testing Locally](#testing-locally)  
8. [Troubleshooting](#troubleshooting)  
9. [Roadmap](#roadmap)  
10. [License & Credits](#license--credits)

---

## Features
| Area | Highlights |
|------|------------|
| **LLM Orchestration** | *Gemini 2.5 Pro* for planning; *OpenAI o3* for repair (20 k chat / 25 k repo-map limits). |
| **Scaffold Choices** | `create-expo-app` (React-Native) · `flutter create` (web/desktop) · `create-next-app` (Next.js). |
| **Backend Options**  | Supabase or Firebase stubs; real calls are commented until you wire secrets. |
| **Doc-Aware RAG**    | Only the matching sections of the backend docs are embedded with **Chroma DB** and fed to Aider. |
| **Test Matrix**      | ESLint + Jest unit tests · Detox Android/iOS E2E · Flutter `integration_test`. |
| **Remote iOS Flow**  | Non-Mac users paste a PAT; a Fastlane `build_ios_app` job runs on GitHub’s macOS runner. |
| **Quota Guards**     | Aborts if OpenRouter credits < 10 % or GitHub Actions minutes < 100. |
| **Caching**          | Gradle, AVD & npm caches reduce CI runtime to ~ 5 minutes. |

---

## Repository Map
```
AiderGen/
├─ pyproject.toml          · project metadata
├─ bump_version.py         · syncs __version__ with latest git tag
├─ detox.config.js         · Android E2E template
├─ e2e/first.spec.js       · sample Detox test
├─ .github/workflows/
│  ├─ ci.yml               · Linux unit + Detox + Flutter int
│  ├─ ios.yml              · remote iOS build
│  └─ publish.yml          · tag → PyPI wheels
└─ aidergen/
   ├─ cli.py        ├─ llm.py          ├─ quota.py
   ├─ utils.py      ├─ unmet.py        ├─ embed.py
   ├─ scaffolder.py ├─ runner.py       └─ ios.py
```

---

## Prerequisites
| Tool | Version |
|------|---------|
| **Python** | 3.9 + |
| **Node.js** | 18 + |
| **GitHub CLI** (`gh`) | latest |
| **Flutter SDK** | 3.19 + (for Flutter targets) |
| **Android SDK** | an AVD named **Pixel_4_API_33** (Detox default) |

---

## Installation
```bash
# recommended: isolated install
pipx install aidergen

# dev install
git clone https://github.com/yourname/AiderGen.git
cd AiderGen && pip install -e .
```

---

## Quick Start
```bash
export OPENROUTER_API_KEY=sk-…

# scaffold a React-Native app targeting Web+Android, with Supabase stubs
aidergen init MyApp --framework rn --targets web,android --backend supabase

cd MyApp
aidergen build   # Aider loops + tests
aidergen run     # launches dev server & emulators
```
*Need iOS on Windows/Linux?*  When prompted, paste a GitHub PAT with `workflow` scope; AiderGen builds the `.ipa` remotely and prints a download link.

---

## Architecture
### 1. Requirement Capture  
Gemini asks questions until you type **DONE**; outputs YAML `requirements.md`.

### 2. Aider Loop  
* Pass 1 (Gemini) implements missing symbols.  
* If tests fail, logs feed back to Aider with **o3** for targeted repair.

### 3. Backend-Aware RAG  
Only matching doc chunks from Supabase/Firebase are embedded and injected into every Aider prompt.

### 4. CI/CD  
* **ci.yml** – ESLint, Jest, Detox (AVD cache), Flutter integration.  
* **ios.yml** – optional Fastlane `build_ios_app` on macOS.  
* **publish.yml** – auto-bumps version, builds wheels with cibuildwheel, publishes to PyPI.

### 5. Quota & Cost  
`quota.py` checks OpenRouter `/usage` and GitHub billing; the CLI prints remaining credits/minutes at the end of each **build** session.

---

## Testing Locally
```bash
# unit + lint
npm run lint && npm test

# Detox Android
npx detox build --configuration android.emu.release --headless
npx detox test  --configuration android.emu.release --headless

# Flutter integration tests
flutter test integration_test
```

---

## Troubleshooting
| Symptom | Resolution |
|---------|------------|
| `ripgrep --json` not supported | Tool auto-installs a static rg 13 binary in `~/.aidergen/rg`. |
| “OpenRouter credits low” error | Top-up credits or tweak threshold in `quota.py`. |
| Detox emulator flakiness | Add `--retries 2` or switch to physical device. |

---

## Roadmap
* Automated TestFlight / Play Internal deploy.  
* Electron GUI wizard.  
* Multi-LLM fallback chain (Claude 3, Mixtral 8×7 B).

---

## License & Credits
* **MIT License** – see `LICENSE`.  
* Powered by OpenRouter, Aider, Detox, Expo, Chroma DB, Fastlane, Supabase JS, Firebase JS SDK, Flutter, and ripgrep.

---

*Happy hacking – create, test & deploy, all from one prompt!*