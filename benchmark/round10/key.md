# Round 10 key

Don't read this before answering the batch.

Question types, as in round 1:
- **control**: a rule the skill already states, asked again. If a control fails, stop the round:
  the instrument or the rule is wrong.
- **gap**: no rule decides it yet.
- **provocation**: an option written to argue one position.

Taxonomy codes F1–F10 and K1–K7 are defined in `README.md`.

## Batch 1

| q | original | type | dimension | probes | source |
|---|---|---|---|---|---|
| R10-Q01 | B | control | `comments.style_justification` | R9-02: a comment never explains why the file conforms to a style rule. Expect A. | `benchmark/round3/p1_scan_ingest/a_procedural.py:329` |
| R10-Q02 | A | control | `comments.citation_leak` | R7-D04-comments: no decision id in generated code. Expect B. The inline comment on `global LOG` is removed from both options. | `validation/v1_log_triage/skill.py:73` |
| R10-Q03 | B | control | `comments.block_labels` | R8-block-comments: a short label above a blank-separated block. Expect B. | `validation/v4_quota_reconcile/skill_r2/quota_reconcile/usage_text.py:38,44` |
| R10-Q04 | B | control (analogue) | `comments.changelog_tense` | F2a. No code-comment rule exists; R9-06 bans narrating development in the skill's own docs. Expect A. A failure here is a finding, not a broken instrument. | `skill/verify.py:150` |
| R10-Q05 | — | control | `comments.todo_vs_fixme` | R6-12: deferred work in running code is `TODO`; `FIXME` blocks a merge. Expect B. Constructed: the corpus has no TODO or FIXME. | built on `benchmark/round3/p1_scan_ingest/a_procedural.py:452` |
| R10-Q06 | A | gap | `comments.restates_code` | F1, inline. The `ValueError` is the documented behaviour of `fromisoformat`. | `validation/v1_log_triage/base.py:144` |
| R10-Q07 | B | gap | `comments.absent_alternative` | F1 + F8: describes the loop by the alternative it is not. | `validation/v5_billing_reconcile/skill/reconcile/scan_json.py:57` |
| R10-Q08 | A | gap | `comments.changelog_block` | F2a, whole block. Holds a real reason (raise is in every two-line guard) wrapped in history. Keep or delete only; the tense rewrite is a later question. Citation `(R8-D18)` removed from the original. | `git show 7dfdb3e:skill/checks.py`, line 370 |
| R10-Q09 | B | gap | `comments.fixed_bug_guard` | F2 subtype: a warning against reintroducing a fixed bug, told as the bug's history ("scored zero"). | `validation/prepare_blind.py:85` |
| R10-Q10 | A | gap | `comments.style_justification` | F3 at the DB-API exception: the alias exists because of an outside constraint *and* a style rule. Tests whether F3 survives when the constraint is real. | `validation/v3_manifest_audit/skill/manifest_audit/store.py:71` |
| R10-Q11 | B | gap | `comments.nonlocal_claim` | F7: "the one place that builds it", and who calls it. | `validation/v3_manifest_audit/full/manifest_audit/audit.py:78` |
| R10-Q12 | B | gap | `comments.maintainer_instruction` | F9 isolated: the same reason with and without "Change this where...". Seed pair 2 suggests a directive can be good. | `validation/v3_manifest_audit/full/manifest_audit/requirements_lock.py:24` |

## Batch 2

"Paraphrased" means the construction comes from a comment Claude wrote in one of the user's private
projects, rewritten into neutral code because this repository is public.

Batch 2 options use the English style from batch 3, at the user's request. The `original` column
gives the option rewritten from Claude's comment, not a verbatim one.

| q | original | type | dimension | probes | source |
|---|---|---|---|---|---|
| R10-Q13 | A, paraphrased | gap | `comments.candor` | F10 against K7: a justification of why a known weakness is fine, against a TODO naming it. Tests R10-candor in code. | paraphrased |
| R10-Q14 | A | gap | `comments.business_case` | The kind of reason: an outside business case (R10-business-case) against a design argument with an absent alternative (F8). | constructed |
| R10-Q15 | — | gap | `comments.business_case_lapse` | Whether a business case names the condition under which it stops holding. Also F9: the added sentence is a directive. | constructed |
| R10-Q16 | B | gap | `comments.causal_hops` | 2 steps, 1 step or 0 steps of reason, claim held. The `fsum` half of the original is removed from every option. Seed pair 2 axis. | `validation/v2_drift_checker/skill.py:294` |
| R10-Q17 | A, paraphrased | gap | `comments.precision` | An exact mechanism against a shorter, looser one. Seed pair 2 axis. | paraphrased |
| R10-Q18 | — | withdrawn | `comments.absent_alternative` | Withdrawn before it was asked: R10-Q07 decided the `X rather than Y:` frame. | `benchmark/round3/p1_scan_ingest/c_parse_dont_validate.py:294` |
| R10-Q19 | A, paraphrased | gap | `comments.assumption` | Candor: an absolute assertion about input the function does not control, against a stated assumption. | paraphrased |
| R10-Q20 | B, paraphrased | gap | `comments.deliberately` | `Deliberately` alone. Claude uses deliberately / on purpose / by design 17 times as often as the human baseline. | paraphrased |
| R10-Q21 | B | gap | `comments.conversation_residue` | F2b. The example was written right after a reviewer asked for case-sensitive comparison. Is it residue or a useful illustration? | `edits/v5baseC2_R.diff` |
| R10-Q22 | B | gap | `comments.restates_solution` | A K2 reason followed by a sentence describing the code below it (F1). | `validation/v5_billing_reconcile/skill/reconcile/store.py:83` |
| R10-Q23 | B | gap | `comments.data_history` | History of the data (legitimate) against history of the code (F2a), same fact. B is constructed. | `edits/v5full_C4.diff` |
| R10-Q24 | A | gap | `comments.nonlocal_claim` | F7 in a docstring: a claim about another caller that no tool checks. | `edits/v5base_C1.diff` |

## Batch 3

| q | original | type | dimension | probes | source |
|---|---|---|---|---|---|
| R10-Q25 | A | gap | `prose.fragment_compression` | Full noun phrase against a compressed fragment, inline annotation (K4). | `validation/v4_quota_reconcile/full/quota_reconcile/vocabulary.py:96` |
| R10-Q26 | — | gap | `prose.fragment_case` | Capital and period against lowercase and none, on a verbless fragment. | paraphrased from `validation/v1_log_triage/skill.py:234` |
| R10-Q27 | — | gap | `prose.note_prefix` | `NOTE:` marker. Absent from the generated corpus; present in seed pair 2 and in human comments. | constructed |
| R10-Q28 | — | gap | `prose.contraction` | `Do not` against `Don't`. Claude almost never contracts; humans and seed pair 2 do. | constructed |
| R10-Q29 | — | gap | `prose.first_person` | `We` against a subjectless imperative. `we` is 10 times as common in the human baseline. Person and mood move together here. | constructed |
| R10-Q30 | — | gap | `prose.article_identifier` | `The` before a code identifier. From the user's critique of claudish-to-english. | paraphrased |
| R10-Q31 | — | gap | `prose.agentive_verb` | `finds` (implies a search, or agency) against `loads`, and against a subjectless imperative. From the user's critique. | paraphrased |
| R10-Q32 | — | gap | `prose.possessive` | Seed pair 1 in neutral code: possessive against relative clause with a container verb. | paraphrased |
| R10-Q33 | A | gap | `prose.clause_joining` | Semicolon, two sentences, or a dash. | `benchmark/round3/p1_scan_ingest/a_procedural.py:466` |
| R10-Q34 | — | gap | `prose.placement` | End-of-line against above-line. | constructed |
| R10-Q35 | — | gap | `prose.identifier_marking` | `name()`, bare `name`, or backticks. | constructed |
| R10-Q36 | — | gap | `prose.caps_emphasis` | Capitals for emphasis. B paraphrases the original's `must never mutate`; A adds the capitals. | `validation/v2_drift_checker/base.py:518` |
| R10-Q37 | B | gap | `comments.changelog_tense` | The rewrite R10-Q08 deferred: present-tense fact against the history, content held. | `git show 7dfdb3e:skill/checks.py`, line 370 |
| R10-Q38 | — | gap | `comments.uncertainty` | Candor in form: an unverified fact stated as certain, against the assumption stated as one. | constructed |
| R10-Q39 | — | gap | `prose.personification` | An abstract noun as the agent of a verb that needs one (`costs`, `earns`, `keeps`, `decides`), against the literal statement. Raised by the user's objection to "An outside API constraint keeps its comment". | paraphrased |
| R10-Q40 | — | gap | `prose.pseudo_cleft` | `X is what Y` against `X Y`. `is what` runs at 9 per 10,000 words in Claude's comments and near 0 in the human baseline. | constructed |
| R10-Q41 | — | gap | `prose.its_own` | `its own` against the plain determiner, in a case where "not shared" is true and matters. 8 per 10,000 words against near 0. | constructed |

## Batch 4

Every comment is on neither list in `SKILL.md`, **Comments**. Each `keep` is a candidate entry for
**Valid comment topics**. If every one is cut, the list is closed. The comments are written in the
batch 3 English.

| q | type | category | source |
|---|---|---|---|
| R10-Q42 | gap | numerical precision | `validation/v2_drift_checker/skill.py:294`, second half, rewritten |
| R10-Q43 | gap | external specification reference | constructed |
| R10-Q44 | gap | security rationale | constructed |
| R10-Q45 | gap | concurrency invariant | constructed |
| R10-Q46 | gap | regex explanation | constructed, after `validation/v4_quota_reconcile/*/sizes.py` |
| R10-Q47 | gap | test-case annotation (K5) | `validation/v2_drift_checker/base.py:602` |
| R10-Q48 | gap | performance rationale | constructed |
| R10-Q49 | gap | value semantics of `None` (K4) | constructed |
| R10-Q50 | gap | error-handling breadth | constructed |
| R10-Q51 | gap | provenance of a magic number | constructed |
| R10-Q52 | gap | external ticket reference | constructed; the ticket id is fictional |
| R10-Q53 | gap | order dependency between statements | constructed |
| R10-Q54 | gap | domain meaning of an edge case | constructed |
| R10-Q55 | gap | non-obvious algorithm step | constructed |
