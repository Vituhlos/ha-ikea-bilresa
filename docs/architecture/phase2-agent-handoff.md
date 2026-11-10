# Phase 2A — maintainer-authorized GitHub Issue → Codex Cloud handoff

**Status:** PR proposal. Not enabled on the default branch until reviewed and merged.
**Goal:** start useful issue-driven AI development with existing Codex Cloud access,
without a server, a custom GitHub App, an OpenAI API key, or autonomous merging.
**Owner:** @Vituhlos. This stage does **not** run an AI model.

## Rychlý postup (česky)

1. Otevři libovolné existující **otevřené GitHub Issue** v repozitáři
   Vituhlos/ha-ikea-bilresa. Neřeš několik issues najednou.
2. Napiš jako @Vituhlos nový komentář přesně:

   ~~~text
   /agent prepare dev
   ~~~

   pro novou funkci do vývojové větve agent/panel-0.6.1. Pro opravu stabilní
   větve main místo toho napiš:

   ~~~text
   /agent prepare main
   ~~~

3. GitHub Actions spustí workflow **AI issue handoff (manual, no model calls)**.
   Výsledkem bude jeden komentář od github-actions[bot] se zadáním pro Codex
   Cloud. Při opakovaném příkazu pro stejné issue a stejný cíl se komentář
   aktualizuje a nevznikají kopie. Pokud komentář chybí, zkontroluj běh
   workflow v záložce Actions.
4. Otevři https://chatgpt.com/codex, zvol cloudový úkol pro repozitář
   Vituhlos/ha-ikea-bilresa a pokud to rozhraní umožňuje, správnou cílovou
   větev. **Ručně zkopíruj připravené zadání z issue do Codexu.**
   Samotný komentář /agent prepare Codex **NESPUSŤÍ**. GitHub Codespaces
   pro tento proces nemusí být zapnuté.
5. Po dokončení zkontroluj Codex změny, vytvoř **draft PR** (nebo ho nech
   vytvořit Codexem, pokud jeho prostředí tuto možnost nabízí) a zkontroluj
   správnou cílovou větev. Požaduj standardních šest CI kontrol; použij
   CodeRabbit, Codex Review a fyzický BILRESA test, je-li relevantní.
   **Merguje a vydává pouze správce.**

Alternativa: na GitHubu v **Actions → AI issue handoff (manual, no model calls)
→ Run workflow** zadej číslo issue a cíl dev/main. Spuštění je povoleno
pouze účtu @Vituhlos. Po merge bude workflow dostupné na defaultní větvi.

## Technical contract (English)

### What is actually automated now

- Workflow: .github/workflows/ai-issue-handoff.yml
- Trusted logic: tools/agent_handoff.mjs
- CI/unit tests: tests/agent_handoff.test.mjs
- Trigger: issue_comment(created) only when the **actor is Vituhlos** and
  the command is one of the two exact allowed forms, or a maintainer-only
  workflow_dispatch with validated inputs.
- Workflow uses the **default-branch checkout only**, never a PR's or
  reporter's arbitrary branch, and does not evaluate issue content as
  JavaScript, shell commands or a GitHub Actions expression.
- Workflow token scope is contents:read + issues:write, and checkout has
  persist-credentials:false. No external API key, service token, or
  GitHub App private key is configured.
- Issue description is copied **as untrusted task context**, limited to
  12,000 characters, and wrapped with repository/hardware rules. For longer
  reports, review the original issue manually.
- If the same issue+target was previously prepared by github-actions[bot],
  update that comment rather than posting a duplicate.
- **Never** auto-assign to Codex, create agent branches, alter source code,
  open PRs, merge PRs, release, or change Home Assistant configuration.

### Security limitations

- This is a *handoff* rather than a full autonomous coding agent. Explicit
  manual transfer to Codex Cloud prevents surprise AI usage and billing.
- A trusted maintainer can choose an issue written by anyone. Issue title,
  body, logs and comments can contain misleading instructions. Codex must
  treat that text as untrusted task evidence, obey AGENTS.md and confirm
  authorization before behavior-changing work.
- The workflow republishes the public issue description in a public
  comment. Do not paste passwords, tokens, private MQTT addresses, or
  sensitive Home Assistant data into GitHub issues.
- Do not use issue_comment/pull_request_target jobs with secrets that checkout
  and execute untrusted pull-request code.
- For changes to Matter events, gesture semantics or target control,
  automated CI is *not* a replacement for physical tests documented in
  docs/HARDWARE_TEST.md and PROJECT_STATUS.md.
- PRs targeting main and agent/panel-0.6.1 remain protected by active
  GitHub rulesets with six mandatory checks and human-controlled merge.

### What would be necessary for bilresa-assistant[bot]

The separate identity is a **GitHub App**, not an AI service. GitHub App
registration/installation is an owner/admin action and has **not** been done.

Before enabling a fully automatic issue → code → draft PR workflow:

1. Choose a verified execution backend: e.g., GitHub Copilot's third-party
   agent integration on an eligible paid **Copilot** plan, or OpenAI's
   codex-action/Agents API with **separately billed API usage**. GitHub Pro
   and ChatGPT Plus do not themselves provide a free unattended GitHub
   Actions → Codex task API.
2. Confirm operating costs and require explicit owner authorization.
3. Register a GitHub App, install only for this repository, and grant least
   privilege (repository metadata read; contents and pull requests write;
   issues read or write only if required; read-only status/check access as
   needed). Do not grant administration, secrets or workflows write, or
   any protected-branch bypass.
4. Keep the GitHub App signing key private in GitHub secrets/vault; issue
   short-lived installation tokens only inside trusted workflows.
5. Keep issue assignment trusted and bounded (owner-trigger, one issue per
   task, budget and time limits, capped retries, branch allowlist, untrusted
   context handling). Ensure bot-created PRs actually trigger the existing
   protected CI check contexts. Keep draft status and manual merge.
6. Only after testing a real owner-approved example should any automatic
   forwarding or code generation be turned on. Never assume a GitHub App
   alone has an AI backend.

The public NSPanel-Easy panel-easy-assistant app demonstrates the identity
pattern, but does not expose enough of its private backend to justify
copying or claiming its runtime/cost model.

## Phase 2A acceptance checks

- Node unit tests pass, including untrusted inputs and owner-only controls.
- Existing six GitHub CI jobs pass on the PR.
- No secrets, paid API calls, servers, new required status checks or hardware
  changes are introduced.
- After the PR is merged: the owner issues /agent prepare dev on one safe
  open issue and verifies that the GitHub Actions bot posts a task prompt;
  repeats it once to confirm idempotent updating (if desired).
- A later Codex Cloud task is explicitly started by the owner; an agent-built
  PR must target the correct protected base branch and pass review.

**Hardware:** no BILRESA code changes in this stage; hardware validation
not applicable. A later agent-created functional PR is separately gated.
