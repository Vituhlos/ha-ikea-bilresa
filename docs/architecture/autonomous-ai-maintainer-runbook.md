# Contribution snapshots — Stage I / Etapa I

**Implementation scope:** chapter 16 of [the approved proposal](autonomous-ai-maintainer.cs.md).
This runbook does not activate stages II–IV. No AI backend, AI credential,
publisher, coding controller, automatic analysis trigger or GitHub Settings
change is included. Monthly BILRESA Assistant budget stays **500 AIC**;
each Stage I snapshot makes **zero inference calls and spends zero AIC**.

## English: operating the diagnostic

After an explicitly approved push, PR and eventual owner-controlled merge,
the owner may select Actions → **Contribution assessment snapshot (read-only,
no AI)** → Run workflow, branch `main`, and enter one positive issue/PR number.
It accepts only the original owner and owner reruns, in this repository, on
`main`. Before merge the workflow is not available on the default branch.
No remote dispatch was performed during implementation.

The job checks out its immutable trusted main revision, with persisted Git
credentials disabled. It uses Node 22 and only the built-in, repository-scoped
read `GITHUB_TOKEN`; there is no paid API key. Read access: contents, issues,
pull requests and checks. No fork checkout, hooks, dependency installation,
test execution from the assessed PR, external issue URLs or shell evaluation
of input text occurs. Dependencies of the new tool: Node standard library only.
Existing CI, rulesets and `/agent prepare` remain unchanged, except that the
existing **Frontend checks** job also runs the new tool's offline tests.

Outputs are Actions summary, `report.json` (14 days) and `state.json` receipt
(90 days), uniquely named by run ID and attempt. Public repository artifacts
and summaries are **not private**. They contain hashes, source links, symbol
names, line numbers and bounded metadata; no issue/comment bodies, source
text, patches, credentials or arbitrary rendered Markdown. Opening linked
sources still exposes untrusted contributor material. Output size is capped
at 2 MB. Retention and quotas can shorten availability; missing state never
establishes permission to spend. Standard Actions/storage quotas still apply.

### Local read-only use

Use a supported Node 22+ environment and an existing read-only GitHub token
if authenticated API access is necessary. The CLI reads `GH_TOKEN`; it does
not create credentials or load an AI key. Set environment values as data:

```powershell
$env:SNAPSHOT_ITEM = '70'
$env:SNAPSHOT_TOOL_SHA = git rev-parse HEAD
$env:SNAPSHOT_OUTPUT = 'snapshot-output/run-70'
node tools/ai_maintainer/snapshot.mjs
```

Do not paste a token into shell history. Use a new output directory each run;
exclusive file creation refuses to overwrite existing receipts. Exit 0 means
the bounded collection completed, 2 means an incomplete report was saved,
and 1 means the run failed without a usable complete report. The CLI never
publishes. Read failures are deliberately logged without API response bodies.
Some local Windows certificate environments need Node's system CA option;
do not disable TLS verification. The Actions runner uses the normal trust store.

`SNAPSHOT_PREVIOUS` may point to a previous **schema-valid local report**, at
most 2 MB, to display `unchanged`, `evidence-only`, `analysis-input-changed`,
`new-evidence` or `incomplete`. This is an untrusted scheduling hint only.
Stage I deliberately does not restore Actions cache/artifacts as authority or
skip fresh reads. Future paid scheduling must first verify receipt provenance.

```powershell
node --test tests/ai_maintainer/*.test.mjs
node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs tests/agent_handoff.test.mjs
```

### Interpreting evidence

The map in `.github/ai-maintainer/branches.json` resolves latest non-prerelease
tag to its commit, main, development, and (for PRs) actual base and head. PR
merge-preview SHA is never substituted for head. A second read detects moving
refs/item/comments. Related merged PR ancestry is checked independently for
stable/main/development; cherry-picks can have different ancestry. Exact symbol
hashes and lexical observations help review implementations across divergence.
Neither ancestry, matching text nor a matching symbol hash proves equivalent
behavior in different surrounding code.

Explicit local references, timeline cross-references and shared significant
title terms select related candidates. All open PRs are also inventoried to
expose work in progress. Unrelated open-inventory head changes update evidence
only; they do not change the analysis fingerprint. Candidate discovery is
bounded and cannot prove absence of every semantic duplicate. Source selection
is the trusted evidence-path list plus **every PR changed/previous path**,
within a 20-path limit. A complete immutable Git tree records verified path
absence explicitly (including added/deleted/renamed files across revisions).
Unavailable/truncated trees, failed reads of existing files, excess paths, binary
files and symlinks mark it incomplete. Tree modes reject symlinks before the
Contents API can dereference them; blob SHAs must match the tree.
The PR files endpoint is paginated and checked against `changed_files`; the
API's 3,000-file ceiling cannot silently pass. Compare API is used only for
ancestry, never as a complete file list.

The Python symbol index includes enclosing class/function scopes and disambiguates
repeated definitions within a scope. It and the named observations are lexical, not an AST or
automatic classification. The report always asks for human assessment:

- #70: first-notch zero-transition observations on stable/main/dev; the later
  batch smoothing already on main/dev does not satisfy the requested default.
- #9: #14 ancestry and source observations show existing work; original
  reporter validation and the remaining hardware checklist must be reviewed.
  There is no new comment, closure or stale-policy change here.
- #71: four zero-bound `or default` observations on each target branch and
  stable, versus none on the contributor PR head, which has four explicit
  `None` checks; retain that PR and authorship.
  Head-pinned CI is recorded separately from unit tests run by this tool (none)
  and from hardware. A skipped optional job remains skipped.

Checks count only at the exact head, with the configured context and GitHub
Actions App ID 15368. Missing, duplicate, wrong-App, skipped or non-success
required checks do not establish CI. This snapshot does not certify mergeability,
all review decisions, branch-rule enforcement or physical behavior.

## Persistent state and future accounting contract

The strict versioned report and receipt schemas reject unknown fields and
invalid types. Receipts bind repository/item, report digest, both fingerprints,
policy/tool content digest, base tool commit, time, run ID and rerun attempt.
Local uncommitted tools are identified by their content digest in addition to
the base commit. This is integrity metadata, **not a signature**. A downloaded
artifact must later be verified against its repository, workflow, exact trusted
workflow revision, run/attempt and digest. Never trust model-supplied approvals,
receipt fields, artifact names or cache hits as authorization.

The analysis fingerprint includes normalized item title/body/state/labels,
human comments and reviews, relevant related work, file identities, exact refs
and policy/tool digest. It excludes timestamps, operational bot prose and check
status. CI changes affect the separate evidence fingerprint. Human edits and
deleted comments, source movement, force pushes and policy changes invalidate
analysis. A human spoofing a bot marker is still included. Bot-authored review
prose is intentionally not used in Stage I and must be inspected manually.

**The receipt is not a monthly budget ledger.** `spent=0`, `reserved=0` describe
this diagnostic only. `monthlyBalance=null`, `authorizesSpending=false` and
`authorizesPublication=false` are mandatory. `spendingDecision()` refuses all
inputs. No reservation, spending, model session or public-output state writer
is implemented in this PR.

Before Stage II, a separately reviewed persistent ledger must support all of:

| Record/operation | Required contract |
|---|---|
| Monthly identity | Repository ID + UTC `YYYY-MM`; fixed 500 AIC cap, trusted reconciliation status and monotonic revision |
| Attempt identity | Task ID + run ID + run attempt; retries are distinct chargeable attempts |
| Reservation | Atomic compare-and-swap/transaction before inference; reserve maximum cost under shared daily/monthly limits |
| Settlement | Provider usage evidence and units, measured AIC, time and previous ledger digest; never accept model estimates as accounting |
| Uncertain result | Running/cancelled/unsettled attempt retains its full reservation; measured overruns count in full and stop further admissions |
| Recovery | Missing/corrupt/expired ledger or unclear prior attempt fails closed; reconcile provider usage and existing outputs before retrying |
| Human approval | Approver ID, exact scope/text hash, target refs, expiry; mutation invalidates approval |
| Coding identity | Repository/item + approved scope + target branch, independent of moving tips; reconcile existing session/draft PR before another attempt |
| Limits | 150 AIC/day; 5 issue, 50 PR, 150 coding AIC/attempt; 5 analyses/day, 2/item/day; one paid session, at most 4 coding sessions/month, all under 500 AIC |

Use immutable receipts for audit and a **durable transactional authority** for
admission. An Actions cache or a succession of success-only artifacts cannot
provide that guarantee. Actions concurrency alone is not a durable queue or
an atomic ledger; a pending job can be replaced. The concrete transactional
storage adapter, billing reconciliation and reservation/cancellation tests are
activation gates for Stage II, not implicit authorization to create a service,
secret or state branch now. Manual dispatch must pass the same admission gate.

## Next gates and rollback

1. Owner reviews this local change and explicitly approves push/PR. Existing
   six checks must then pass in GitHub; local tests do not establish CI.
2. After an owner-controlled merge, manually exercise the diagnostic and inspect
   artifact provenance, output retention and permission failures.
3. Separately approve Stage II: Copilot Pro/gh-aw pilot, verified account billing,
   transactional ledger, isolation of credentials, model availability and limits.
4. Separately approve a publisher, then automatic triage. Before public responses,
   address existing `stale.yml` auto-close behavior, including already-labelled #9.
5. Coding requires its own approval, author-preserving workflow and actual CI.

For Stage I rollback, stop dispatching this optional workflow or remove it in
an owner-reviewed PR. Preserve receipts for audit. Do not alter normal CI,
rulesets, `/agent prepare`, branches, releases or Home Assistant. The future
AI/public/coding flags all remain false; changing them alone cannot activate
anything because no AI or writer backend exists here.

## Česky: provoz, stav a omezení

Po samostatně schváleném pushi, PR a případném merge správcem lze v Actions
ručně spustit **Contribution assessment snapshot (read-only, no AI)** na `main`
s číslem issue/PR. Povoleni jsou pouze vlastník a jeho opakované běhy. Workflow
nebylo při implementaci vzdáleně spuštěno. Používá pouze čtecí `GITHUB_TOKEN`,
Node 22 a standardní knihovnu; nevytváří API klíč ani nevolá AI. Měsíční limit
zůstává **500 AIC**, spotřeba Etapy I je **0 AIC**.

Pro místní běh použij příkazy výše, případný existující čtecí token poskytni
bezpečně přes `GH_TOKEN` a pokaždé zvol nový výstupní adresář. Návratový kód 0
značí dokončený omezený sběr, 2 uložený neúplný report a 1 chybu. Žádný kód
neznamená schválení změny. `SNAPSHOT_PREVIOUS` slouží jen k porovnání s předchozím
validním místním reportem; nezakládá důvěru ani právo utrácet. V prostředí Windows
může být nutné zapnout systémové certifikáty Node; ověřování TLS nevypínej.

Report (14 dní) a potvrzení běhu (90 dní) jsou veřejné artefakty. Obsahují jen
omezená metadata, hashe, symboly a odkazy, nikoli těla příspěvků, komentářů či
zdrojové soubory. Odkazovaný obsah je nadále nedůvěryhodný. Výstup má limit 2 MB;
retence a kvóty mohou záznamy odstranit. Chybějící záznam nepovoluje novou spotřebu.
Kód z cizího PR, hooks a závislosti se nespouštějí; texty se nevyhodnocují jako
shell a libovolné URL se nestahují. Běžné kvóty Actions a úložiště zůstávají.

Sběr rozlišuje stabilní tag, `main`, vývojovou větev a přesný base/head PR.
Zachycuje ancestry, související a otevřené PR, hashe metod, lexikální pozorování
a testovací symboly. Shoda není důkaz sémantické duplicity. Kandidáti podle
odkazů či slov názvu nejsou úplným sémantickým vyhledáváním. Limit počtu podkladů,
chybějící stránka, nedostupný podklad nebo pohyb revize vytvářejí neúplný výsledek.
Nepřítomnost cesty ověřená úplným Git stromem se eviduje zvlášť, takže přidání,
smazání či přejmenování souboru není samo o sobě chybou. Režim položky stromu
zachytí symlink ještě před načtením přes Contents API a SHA blobu musí souhlasit.
Identita funkce zahrnuje nadřazené funkce/třídy i rozlišení opakovaných definic. CI se
váže k head SHA, názvu kontroly a App 15368; skipped ani podvržená kontrola
není úspěch. Implementace, Static, Unit, CI, Hardware a Released zůstávají
oddělené. Sběrač nespouští testy posuzovaného PR ani fyzické testy.

Příklady: #70 odlišuje první zářez od již existujícího vyhlazování dalších dávek;
#9 ukazuje hotovou související práci, ale nepotvrzuje původní hardwarový scénář;
#71 ukazuje existující příspěvek autora: na stable/main/dev jsou vždy čtyři
vzory `or default` pro meze, na headu PR žádný a místo nich čtyři kontroly
`None`. Zelené CI se nepovyšuje na fyzické ověření. Nevzniká nový komentář, konkurenční oprava ani uzavření issue.

Fingerprint analýzy ignoruje pouhé časové značky, botí provozní text a přechody CI.
Změna lidského obsahu, relevantního PR, revize či politiky jej mění; změna CI
nebo nesouvisejícího otevřeného PR aktualizuje jen důkazy. Botí review text není
v Etapě I analytickým vstupem a vyžaduje ruční prohlédnutí. Podvržený botí marker
v lidském komentáři obsah nevyřadí. Budoucí placený systém musí důvěryhodně ověřit
původ předchozího výsledku, než podle něj přeskočí analýzu.

`state.json` je auditní potvrzení, **nikoli měsíční účetnictví**. Nulová spotřeba
se vztahuje k tomuto běhu. Měsíční zůstatek je neznámý; oprávnění ke spotřebě
a publikaci jsou vždy false. Hashe nejsou podpis. Budoucí příjemce musí ověřit
repozitář, workflow, důvěryhodnou revizi, run ID, pokus a digest artefaktu.

Před Etapou II je nutná trvalá transakční evidence: identita repozitáře a UTC
měsíce, monotónní revize, atomická rezervace maxima před každým modelem včetně
rerunů, vyúčtování doložené poskytovatelem a konzervativní započtení zrušených
či nejasných pokusů. Naměřené překročení se nesmí oříznout na rezervaci.
Neúplná historie zastaví další práci. Stejné limity platí i pro ruční spuštění:
500 AIC/měsíc, 150/den, 5/issue, 50/PR, 150/coding; 5 analýz/den, 2/položku,
jedna souběžná placená session, nejvýše čtyři coding sessions za měsíc.
Cache, úspěšné artefakty ani samotná Actions concurrency tuto autoritu nenahrazují.
Konkrétní transakční úložiště a jeho testy patří až do samostatně schválené etapy.

Budoucí schválení musí obsahovat identitu správce, hash rozsahu či textu, cílové
revize a expiraci. Coding klíč váže položku, schválený rozsah a cílovou větev,
nikoli pohyblivý head; před novým pokusem se dohledá existující session/draft PR.
Žádný z těchto zápisových mechanismů tento PR neaktivuje.

Další pořadí: schválení publikace tohoto PR → běžné CI → merge správcem a ruční
diagnostický test → samostatný pilot Copilotu s ověřeným billingem a izolací →
samostatný publisher a změna stale politiky včetně #9 → zvlášť povolený coding.
Rollback Etapy I znamená přestat ručně spouštět diagnostiku nebo ji odstranit
schváleným PR. Běžné CI, rulesets, `/agent prepare`, release ani Home Assistant
se nemění. Všechny budoucí aktivační přepínače zůstávají vypnuté.

## API references

- [PR files and its 3,000-file limit](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files)
- [Compare commits and file-list limits](https://docs.github.com/en/rest/commits/commits#compare-two-commits)
- [Check runs for a Git reference](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference)
- [REST pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
