# Decomposing a Metadata Layer: An Ablation Study on Conversational Retrieval

## What this document is

A retrieval-augmented generation experiment over a conversational corpus showed a large improvement when a hand-built metadata layer was added to the index: Precision@5 rose from 0.300 to 0.420 and Recall@5 from 0.505 to 0.812. Those figures on their own say nothing useful. They do not say which part of the metadata layer did the work, whether the parts are redundant, or whether the improvement would survive a different corpus.

This document reports a ten-configuration ablation study designed to answer the first two questions, and states plainly why it cannot answer the third.

It is written as an account of four decisions rather than as a results table, because the results table is reproducible from the repository and the decisions are not.

---

## 1. The system under test

**Corpus.** Forty-seven semantic units, consolidated from 284 segments across ten conversations selected for the proof of concept. Those ten conversations sit within a larger segmentation of 1,014 segments over 66 conversations. The corpus contains personal data and is not published; the code, the scores and this document are.

**Metadata layer.** Each unit carries a `decision_status` value from a seven-concept controlled vocabulary, later formalised in SKOS and published separately with a DOI, together with free-text annotation notes and a list of related units.

**Three mechanisms** were available to the retrieval pipeline:

| Mechanism | What it does |
|---|---|
| Query-side filtering | A rule set maps query wording to expected `decision_status` values and restricts the candidate set before ranking |
| Metadata embedding | The status value and the annotation notes are prepended to the unit's text before it is embedded |
| Relation expansion | Units listed in `related_segments` of the top-ranked results are pulled into the result set |

**Embedding model.** bge-m3, served locally through Ollama, with a 6,000-character truncation limit on the embedded text.

---

## 2. Why topic segmentation, and not fixed-length chunking

Fixed-length chunking has a specific failure mode on conversational data. The message boundary looks like a natural unit and is not one. A decision typically forms across several exchanges: it is raised, questioned, revised, and settled. Chunking at message boundaries cuts that process into fragments, none of which is a decision.

This matters more for the metadata layer than for retrieval. A status value can only be assigned to a unit that contains a complete decision. Applied to a fragment, the question "is this Exploring or Decided" has no answer: the first half of the exchange is exploratory and the second half is committed, and neither state describes the decision. **Topic segmentation is therefore a precondition of the annotation layer, not a retrieval optimisation.**

Segmentation was performed by an LLM over the conversation text. It did not work well. The model produced 284 segments for ten conversations and over-split heavily: a manual pass identified 237 of them as continuations rather than independent units and merged them into anchor segments, an 83% merge rate. The retrieval corpus of 47 units is the output of that manual pass.

Two things follow, and both are stated rather than concealed:

- The automatic step failed at its stated purpose and was rescued by human judgement. The pipeline is reproducible, but the merge decisions are not derivable from the code.
- The merge judgements were made by a single annotator with no second pass and no agreement statistic. The segmentation is defensible as a documented procedure, not as a validated method.

---

## 3. How the test set was built, and what it cannot support

Ten questions, 28 relevance judgements. Two properties of its construction constrain every claim made below.

**The questions were written after reading the corpus.** They are therefore not independent of it: knowing where the answers lay will have shaped how the questions were phrased. This is construct contamination, and it inflates absolute scores by an unknown amount.

**Relevance was judged by one person against self-defined criteria.** There was no second assessor and no agreement statistic, so systematic bias cannot be ruled out.

### What this rules out

Absolute figures are observations on this test set. They are not estimates of method performance and must not be extrapolated to other corpora or tasks. The claim "this approach improves Recall@5 by 61%" is not supported by this study and is not made in it.

### What this leaves intact

All ten configurations were scored against the same corpus, the same questions and the same relevance judgements. Test-set bias raises or lowers the absolute level for every configuration alike; it does not systematically favour one over another. **Between-configuration comparison retains its internal validity, and the mechanism decomposition rests only on between-configuration comparison.**

This is the reason the study is framed as an ablation rather than an evaluation. An ablation asks which component contributes what, and that question does not require the test set to generalise. It requires only that the test set be held constant, which it is.

---

## 4. Configurations

Four switches were varied: whether notes are prepended to the embedded text, whether the status value is prepended, whether query-side filtering is off, applied as a soft score boost, or applied as the original hard filter, and whether relation expansion runs.

| Configuration | notes | status | filter | expand |
|---|---|---|---|---|
| A_baseline | – | – | off | – |
| B_full | yes | yes | hard | yes |
| C_filter_only | – | – | hard | – |
| D_embed_only | yes | yes | off | – |
| E_no_expand | yes | yes | hard | – |
| F_notes_only | yes | – | off | – |
| G_status_only | – | yes | off | – |
| H_all_soft | yes | yes | soft | – |
| I_filter_only_soft | – | – | soft | – |
| J_expand_only | – | – | off | yes |

---

## 5. Results

| Configuration | P@5 | R@5 | Hits / 28 | ΔR@5 vs baseline | p |
|---|---|---|---|---|---|
| A_baseline | 0.300 | 0.505 | 15 | — | — |
| B_full | 0.420 | 0.812 | 21 | +60.7% | 0.031 |
| C_filter_only | 0.360 | 0.720 | 18 | +42.6% | 0.125 |
| D_embed_only | 0.360 | 0.658 | 18 | +30.4% | 0.125 |
| E_no_expand | 0.420 | 0.812 | 21 | +60.7% | 0.031 |
| F_notes_only | 0.320 | 0.622 | 16 | +23.1% | 0.219 |
| G_status_only | 0.280 | 0.552 | 14 | +9.2% | 0.625 |
| H_all_soft | 0.420 | 0.812 | 21 | +60.7% | 0.031 |
| I_filter_only_soft | 0.320 | 0.600 | 16 | +18.8% | 0.375 |
| J_expand_only | 0.300 | 0.505 | 15 | 0.0% | n/a |

Per-question hits, out of the relevance judgements available for each question:

| Configuration | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 |
|---|---|---|---|---|---|---|---|---|---|---|
| judgements | 1 | 5 | 1 | 3 | 1 | 3 | 4 | 3 | 2 | 5 |
| A_baseline | 0 | 1 | 0 | 1 | 1 | 3 | 3 | 2 | 1 | 3 |
| B_full | 1 | 4 | 1 | 2 | 1 | 3 | 3 | 3 | 1 | 2 |
| C_filter_only | 1 | 3 | 1 | 1 | 1 | 3 | 2 | 2 | 1 | 3 |
| D_embed_only | 0 | 3 | 1 | 2 | 1 | 3 | 3 | 2 | 1 | 2 |
| E_no_expand | 1 | 4 | 1 | 2 | 1 | 3 | 3 | 3 | 1 | 2 |
| F_notes_only | 0 | 2 | 1 | 1 | 1 | 3 | 3 | 1 | 2 | 2 |
| G_status_only | 0 | 1 | 1 | 1 | 1 | 3 | 3 | 1 | 1 | 2 |
| H_all_soft | 1 | 4 | 1 | 2 | 1 | 3 | 3 | 3 | 1 | 2 |
| I_filter_only_soft | 0 | 2 | 1 | 1 | 1 | 3 | 2 | 2 | 1 | 3 |
| J_expand_only | 0 | 1 | 0 | 1 | 1 | 3 | 3 | 2 | 1 | 3 |

Percentage changes derive from a denominator of 28 judgements across ten questions. A single additional hit on Q1, which has one judgement, moves Recall@5 by ten percentage points. The per-question table is the honest view; the summary table is a convenience.

### On the p values

The significance test in the experiment script is guarded by a `try` block around the scipy import. scipy was not installed when the study ran, so the function returned `None` for every configuration and the published results table carried no p values. The figures above were computed afterwards from the recorded per-question recall, using a one-sided Wilcoxon signed-rank test against the baseline. No new retrieval was performed; the inputs are the scores already in `ablation_results.json`.

With ten questions the test has very little power. Three configurations reach p = 0.031, which is the smallest value attainable with six non-zero differences, and the rest do not reach significance. **The correct reading is that this study is underpowered, not that filtering alone or embedding alone is ineffective.** The p values are reported because omitting them would overstate the certainty of the point estimates, not because they establish anything.

---

## 6. Decomposing the improvement

Relation expansion contributes nothing, and the data show this twice: `J_expand_only` reproduces the baseline exactly, question by question, and `E_no_expand` reproduces the full system exactly, question by question. The mechanism can therefore be set aside, leaving two.

Their contributions overlap, so neither the individual gains nor the marginal gains are a fair attribution on their own. A Shapley decomposition averages each mechanism's marginal contribution across both possible orderings of introduction:

| Quantity | ΔR@5 |
|---|---|
| Filtering alone (C − A) | +0.215 |
| Metadata embedding alone (D − A) | +0.153 |
| Sum of individual gains | +0.368 |
| Actual joint gain (E − A) | +0.307 |
| **Shapley value, filtering** | **+0.184 (60.1%)** |
| **Shapley value, metadata embedding** | **+0.123 (39.9%)** |
| Redundancy between the two | 0.062, or 16.7% of the summed individual gains |

Roughly six-tenths of the improvement comes from using the status value to constrain the candidate set at query time; roughly four-tenths from putting metadata into the embedded text. The two mechanisms duplicate about a sixth of each other's work.

**The practical consequence for the vocabulary.** Within the embedding channel, the free-text notes carry most of the weight (+0.117 alone) and the status label carries little (+0.047 alone). The status value earns its keep by filtering, not by enriching documents. A controlled vocabulary built for this purpose should therefore be designed as a query-side filtering vocabulary: its scope notes need to state boundary rules precise enough to answer "which records are in this state", rather than descriptions intended to enrich indexed text. An implementation that only prepends the label to the document will realise the smaller share of the benefit.

### Hard and soft filtering are indistinguishable here

`H_all_soft` replaces the hard filter with a score boost and produces results identical to `E_no_expand` on every question. Filtering alone tells a different story: the hard variant reaches 0.720 and the soft variant only 0.600.

So the two variants differ when they act on plain-text embeddings and are indistinguishable when they act on metadata-enriched ones. The reading consistent with the data is that once the metadata is in the embedded text, the documents the hard filter would have excluded already rank below the cut-off, and removing them changes nothing. On this corpus, at this size, the hard filter has no effect that the soft boost does not already achieve — which is a reason to prefer the soft variant, since it degrades more gracefully when the intent rules misfire.

This finding rests on ten questions and one corpus, and should be treated as a hypothesis worth testing at scale rather than a result.

---

## 7. The one regression

Q10 ("what research have I done on the European market") is the only question where the full system does worse than the baseline: three hits against two.

Two mechanisms can be eliminated directly from the recorded run:

- **Filtering is not involved.** The intent rules did not fire on this question. `intent_filter` is null and `hard_filter` is false in both configurations, so the candidate set was never restricted.
- **Expansion is not involved.** `E_no_expand` matches `B_full` on this question as on every other.

That leaves the embedded text. The comparison confirms it: `D_embed_only`, which changes only the embedding, drops to two hits, and both single-channel variants, `F_notes_only` and `G_status_only`, also drop to two.

Looking at what moved:

| | Baseline top 5 | Full system top 5 |
|---|---|---|
| 1 | 014_000 | 019_015 |
| 2 | 019_015 | 014_000 |
| 3 | **014_001** | **014_004** |
| 4 | **064_000** | **014_001** |
| 5 | **014_038** | 019_000 |

Relevant units in bold. The full system gains 014_004 and loses two units that the baseline held at ranks four and five.

**Truncation was the first hypothesis, and it is wrong.** Prepending metadata lengthens the embedded text, so a unit near the 6,000-character limit would lose original content and its vector would shift. Neither lost unit is anywhere near the limit: 064_000 runs to 3,479 characters plain and 3,529 with metadata; 014_038 to 2,194 and 2,237. The prefixes added 50 and 43 characters respectively. No content was truncated from either.

The mechanism is marginal ranking instability. The two units lost sat at ranks four and five, immediately inside the cut-off. Prepending text to every document perturbs every vector, and where the similarity gap between rank five and rank six is smaller than that perturbation, the ordering flips. Nothing about the metadata made those units less relevant; they were close enough to the boundary that a change unrelated to their relevance was sufficient to move them across it.

The single-channel configurations support this. `G_status_only` prepends roughly twenty characters — a status label and two newlines — and produces exactly the same loss as `F_notes_only`, which prepends far more. If the effect scaled with the amount of text added, these would differ. They do not, which is what a boundary effect looks like: what matters is that the vectors moved at all, not how far.

The general point is about top-*k* evaluation rather than about metadata. Recall@5 counts a document at rank five and ignores one at rank six, so every retrieved set has a boundary, and on a corpus of 47 units the similarity gaps at that boundary are small. Any intervention that perturbs the embedding space will reorder items across it in both directions. Here the reordering happened to be net negative on one question and net positive on the other nine.

One regression in ten questions is well within what boundary noise would produce. It is reported because a single unexplained regression is the kind of detail a results table hides, and because tracing it eliminated a plausible-sounding explanation that would otherwise have been recorded as the cause.

---

## 8. What this study does and does not establish

**Established, within this corpus and test set:**

- Relation expansion contributes nothing, shown twice and exactly.
- The improvement decomposes roughly 60/40 between query-side filtering and metadata embedding, with about a sixth of the work duplicated.
- Within the embedding channel, free-text notes contribute about two and a half times as much as the status label.
- Hard and soft filtering are indistinguishable once metadata is embedded.
- The single regression is a boundary effect at the rank-five cut-off, not a truncation artefact; truncation is excluded by measurement.

**Not established:**

- Any absolute performance figure, for the reasons in section 3.
- Statistical significance for individual mechanisms; the study is underpowered at n = 10.
- Generalisation of any finding to a larger corpus, a different domain, or a different embedding model.

**Not attempted:**

- Comparison against established baselines such as BM25 or a reranker.
- Any measure of generation quality; this study covers retrieval only.

---

## 9. What is published

The corpus is the author's own conversation records and contains personal data. It is not published, and neither are the recorded per-question results, because the test questions are themselves personal material.

| Published | Withheld |
|---|---|
| `run_ablation.py`, the experiment code | `retrieval_corpus.json`, the corpus |
| `queries.example.json`, the test set format | `queries.json`, the questions and relevance judgements |
| This document, containing every figure the study produced | `ablation_results.json`, the recorded per-question output |

The code reads the test set from an external file rather than defining it inline, so the published script is complete and runnable against any corpus in the same format. The scores in sections 5 and 6 are reproduced here in full: the per-question hit matrix is the raw numerator behind every mean and every percentage, so no figure in this document rests on a file the reader cannot see.

That the study is not independently reproducible follows from the corpus, not from the choice of what to publish. Where the corpus cannot be released, the honest position is to publish the reasoning and the complete scores and to say which claims that supports — the mechanism decomposition, which depends only on holding the test set constant — and which it does not, which is anything absolute.

The controlled vocabulary developed for the `decision_status` field is published separately, in full, with a DOI and a conformance validation script.
