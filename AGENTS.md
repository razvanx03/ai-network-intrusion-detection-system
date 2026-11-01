# AI Agents Guide & UI Conventions

This file defines coding standards and architectural principles for AI agents working on the **AI NIDS** project.

---

## 1. Testing Policy (Strict Rule)

* **Backend Unit Tests:** The user explicitly authorized backend unit tests. Keep them under `api/tests/unit/`, using pytest and development dependencies from `api/requirements-dev.txt`. Preserve and maintain this suite.
* **Isolation:** Unit tests must not load the real `.env`, open the application database, contact VM agents, or depend on downloaded datasets or deployed model artifacts. Use explicit test configuration and simulated boundary dependencies.
* **Scope:** Do not introduce frontend tests or integration suites unless requested. Focus backend tests on observable business behavior, validation, authentication, AI inference contracts, ingestion progress and failure handling.

---

## 2. Git & Branching Workflow (Strict Rule)

* **No Automatic Branching:** Do NOT create new git branches (`git checkout -b`, `git branch`) on your own. The default is to work directly on the branch where the prompt/session was started. Only create a branch if the user explicitly asks for it.
* **No Automatic Staging, Commits, or Pushes:** Leave all modified and created files unstaged in the working tree. Do NOT execute `git add`, `git commit`, or `git push` automatically. The user decides when and how to stage, commit, and push changes.

---

## 3. Terminology & Naming Convention: Use 'AI' (Never 'ML')

* **Rule:** Do NOT use the abbreviation or directory name **`ml`** or **`ML`** (Machine Learning) when referencing intelligence, detection, or classification components.
* **Standard:** Always use **`AI`** (e.g. folder path is strictly **`app/ai/`**, AI Engine, AI Detector, AI models).

---

## 4. No Academic / Dissertation / Professor Mentions (Strict Rule)

* **Strict Rule:** NEVER mention anywhere in the codebase, UI, translations, comments, `.env`, or documentation (`README.md`) that this is a dissertation/thesis project, the dissertation title, academic requirements, university references, or professors/coordinators.
* Treat and present the project strictly as a standalone, production-grade AI Network Intrusion Detection System (AI NIDS).

---

## 5. Frontend Principles & Component Guidelines

### A. Always Prefer shadcn/ui Components
* **Rule:** Do NOT write raw CSS, raw HTML button elements with ad-hoc styling, or reinvent UI primitives from scratch.
* **Component Library:** Always use or install **shadcn/ui** components (built on Radix UI and Tailwind CSS).
  - Use `Button`, `Card`, `Badge`, `Input`, `Table`, `Dialog`, `DropdownMenu`, `Tabs`, `Separator`, `Tooltip`, etc.
  - Keep styling consistent with the design system and Tailwind theme variables.
  - When a new UI element is needed, add the corresponding shadcn component to `app/src/components/ui/`.

### B. AI & Loading States: `thinking-orbs`
* For agentic operations, background log parsing, AI inference, and loading states, use the **`thinking-orbs`** library:
  - Source: [Jakubantalik/thinking-orbs](https://github.com/Jakubantalik/thinking-orbs)
  - Provides lightweight canvas-rendered animated thought orbs representing distinct agentic states (`working`, `searching`, `solving`, `listening`, `composing`, etc.).
  - Always utilize `thinking-orbs` during long-running actions (e.g., "Preia si analizeaza loguri", "Rulare model AI").

### C. File-Based Routing
* Routes in the frontend are auto-generated from the filesystem structure (using **`@generouted/react-router`**).
* Pages reside under `src/pages/` (e.g. `_app.tsx`, `index.tsx`, `dashboard.tsx`, `login.tsx`, `connections.tsx`). Subdirectories automatically translate into nested routes.
* Do not manually build large monolithic route mapping objects.

### D. Mandatory Build Verification (`npm run build`)
* **Strict Rule:** Always run `npm run build` in the `app/` directory after any frontend modifications.
* The build must compile cleanly with 0 TypeScript/Vite errors before concluding any task. Never leave the frontend with broken builds, unresolved peer dependencies, or runtime router context mismatches.

### E. Clean UI: No Meta Notes or Internal Rules Displayed
* **Strict Rule:** Do NOT display internal implementation details, developer rules, meta-notes, or configuration hints on the UI (e.g. do not render boxes like "Demo Preset: credentials in .env", or helper text explaining code rules or project constraints).
* Keep the user interface clean, professional, and authentic — looking like a production cybersecurity dashboard.

### F. Internationalization (i18n), Single Translations File & Dead Key Cleanup
* **Single File Rule:** All user-facing text across all pages and components must reside in a single translations file (`app/src/i18n.tsx`). Never hardcode UI strings inside JSX or component templates.
* **Delete Unused Translation Keys Immediately (Strict Rule):** Whenever a UI element, section, or text is removed from a component or page, you MUST immediately delete its corresponding translation keys from `app/src/i18n.tsx` (in both `ro` and `en`). Never leave unused/dead translation keys in the codebase.
* **No Diacritics in Romanian (Strict Rule):** For Romanian language strings, **NEVER use diacritics** (strictly use standard Latin letters: `a` instead of `ă`/`â`, `i` instead of `î`, `s` instead of `ș`, `t` instead of `ț`).
* Language switching must be instantaneous and reactive via `useI18n()`.

### G. Settings & Preferences Persistence
* Settings dropdown provides controls for Language (`ro`, `en`) and Theme (`dark`, `light`).
* Both preferences are persisted in `localStorage` (`nids_language` and `nids_theme`).
* Table headers must be visually distinct from data rows (using contrasting background, clear borders, uppercase typography).

### H. No Hotkeys / Keyboard Shortcut Traps (Strict Rule)
* **Strict Rule:** Do NOT attach global keyboard event listeners (`keydown`, `keyup`) or hotkeys that change the theme, language, or UI state on keypress.
* All state mutations and theme changes must be executed strictly via explicit user clicks in the UI.

---

## 6. Backend (API) Principles (Layered Modular Architecture)

* **Separation of Concerns:**
  - **Routes (`app/routes`):** Thin controllers handling HTTP requests, query params, status codes, and delegating to services.
  - **Services (`app/services`):** Pure business logic (orchestrating repositories, AI inference, sensor fetch).
  - **Repositories (`app/repositories`):** Data access layer isolating SQLAlchemy queries.
  - **Models (`app/models`):** SQLAlchemy ORM entities.
  - **Schemas (`app/schemas`):** Pydantic validation models (request/response DTOs).
  - **AI Engine (`app/ai`):** Feature extraction, AI classifiers, anomaly detection algorithms.
  - **Integrations (`app/integrations`):** Sensor Agent HTTP client (with mock fallback for offline testing).
* **Security & Auth:**
  - Single admin authentication with JWT tokens stored exclusively in `HttpOnly` secure cookies.
  - Passwords hashed using `bcrypt`.
  - Sensitive configurations strictly read from environment variables (`.env`).

---

## 7. Strict Fail-Fast Configuration & No Silent Fallbacks (Strict Rule)

* **No Silent Fallbacks:** Do NOT use silent default fallbacks for core configuration or environment variables (e.g. never do `import.meta.env.VITE_API_BASE_URL || "/api"`, `SECRET_KEY = "default-key"`, or catch blocks that return fallback origins or empty datasets).
* **Crash on Missing Configuration:** If an environment variable, `.env` file, database URL, CORS origin list, or mock data sample is missing or malformed, the application MUST fail fast and crash immediately with a clear, descriptive error.
* **Strict Cookie Auth:** Dashboard sessions must rely strictly on `HttpOnly` cookies. Do not fall back to `localStorage` or silent client-side workarounds.
