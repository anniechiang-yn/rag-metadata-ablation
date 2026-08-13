# RAG Metadata Ablation

A ten-configuration ablation study decomposing what a hand-built metadata layer contributes to retrieval over a conversational corpus.

Adding the metadata layer raised Precision@5 from 0.300 to 0.420 and Recall@5 from 0.505 to 0.812. Those figures are not the point. The study exists to answer which part of the layer did the work, whether the parts are redundant, and what the numbers cannot be used to claim.

**[Read the study →](C1_ablation_study.md)**

## What it found

**The improvement splits roughly 60/40.** A Shapley decomposition attributes 60.1% of the gain to using the status value to constrain the candidate set at query time, and 39.9% to prepending status and annotation text to the embedded document. The two mechanisms duplicate about a sixth of each other's work.

**The controlled vocabulary is a filtering vocabulary, not an enrichment vocabulary.** Within the embedding channel, free-text notes contribute about two and a half times as much as the status label. The label earns its place by filtering. This has a direct design consequence: scope notes need to state boundary rules precise enough to answer "which records are in this state", rather than descriptions intended to enrich indexed text.

**Relation expansion contributes nothing on this corpus,** shown twice and exactly: the expansion-only configuration reproduces the baseline question by question, and switching expansion off in the full system changes no result. The field it depends on is populated on 3 of 47 records, so this is a null result about the corpus rather than about the mechanism — reporting it as the latter would be the more impressive claim and the wrong one.

**Hard and soft filtering are indistinguishable once metadata is embedded,** though they differ when applied to plain-text embeddings. Reported as a hypothesis worth testing at scale, not as a result.

**One question regressed, and the first explanation for it was wrong.** The regression was initially attributed to text truncation. The corpus statistics exclude that: prepending metadata pushes no additional unit over the truncation limit, and both lost units sit at under 60% of it. The mechanism is a boundary effect at the rank-five cut-off, and the trace that established it is in [section 7](C1_ablation_study.md#7-the-one-regression).

## What it does not establish

The test questions were written after reading the corpus, and relevance was judged by a single annotator against self-defined criteria. Absolute figures are therefore observations on this test set, not estimates of method performance, and are not extrapolated in the study.

Between-configuration comparison is unaffected, because every configuration was scored against the same corpus, the same questions and the same judgements. The mechanism decomposition rests only on between-configuration comparison. This distinction is set out before the results rather than after them, in [section 3](C1_ablation_study.md#3-how-the-test-set-was-built-and-what-it-cannot-support).

At ten questions the study is underpowered. Three configurations reach p = 0.031 on a one-sided Wilcoxon signed-rank test; the rest do not reach significance.

## Scale

Forty-seven semantic units, consolidated from 284 segments across ten conversations, within a segmentation of 1,014 segments over 66 conversations. Ten questions, 28 relevance judgements. Embedding model bge-m3, served locally through Ollama.

Ranking the top five from a pool of 47 is an easier task than retrieval over a full corpus. The figures should be read accordingly.

## Files

| File | Contents |
|---|---|
| `C1_ablation_study.md` | The study, including every figure it produced |
| `run_ablation.py` | The experiment. Reads a corpus and a test set, writes per-question results and a contribution table |
| `queries.example.json` | Test set format |

The corpus is the author's own conversation records and contains personal data. Neither it nor the test set is published, and nor are the recorded per-question results, since the questions are themselves personal material. The study therefore cannot be independently reproduced. Every score it produced is reported in full in the document, including the per-question hit matrix that is the raw numerator behind every mean and percentage.

## Related

The `decision_status` field was formalised as a W3C SKOS controlled vocabulary and published in full, with a DOI and a conformance validation script: [decision-status-skos](https://github.com/anniechiang-yn/decision-status-skos) · [10.5281/zenodo.21899592](https://doi.org/10.5281/zenodo.21899592)

## Running it

```bash
pip install requests scipy
cp queries.example.json queries.json   # then edit with your own test set
python3 run_ablation.py
```

Requires a running Ollama instance with the `bge-m3` model, and a corpus at `retrieval_corpus.json` in the format the script expects. Embeddings are cached by content hash, so re-runs do not recompute vectors.

## Licence

CC BY 4.0 for the documentation; MIT for the code. See `LICENSE`.
