"""
Ablation study: decomposing what the metadata layer contributes to retrieval.

Reads the same retrieval_corpus.json as run_naive_rag.py and run_metadata_rag.py,
and modifies neither.

Usage:
    cd into the project folder, make sure Ollama is running, then:
    python3 run_ablation.py

    To exercise the script logic without calling Ollama (produces meaningless
    scores; verifies only that the pipeline completes):
    MOCK=1 python3 run_ablation.py

Outputs:
    ablation_results.json   full per-question results for every configuration
    ablation_table.md       contribution table, ready to paste into a document
    embed_cache.json        embedding cache, so re-runs do not recompute vectors

The test set is read from queries.json, which is not published: the questions
are personal material. See queries.example.json for the format.
"""

import json
import math
import os
import hashlib
import sys

OLLAMA_EMBED = "http://localhost:11434/api/embeddings"
CORPUS_FILE = "retrieval_corpus.json"
QUERIES_FILE = "queries.json"
CACHE_FILE = "embed_cache.json"
MOCK = os.environ.get("MOCK") == "1"

# ---------------------------------------------------------------
# Test set. Each key is a query string, each value the segment IDs
# judged relevant to it.
# ---------------------------------------------------------------

if not os.path.exists(QUERIES_FILE):
    sys.exit(f"{QUERIES_FILE} not found. See queries.example.json for the format.")

QUERIES = json.load(open(QUERIES_FILE, encoding="utf-8"))
QUERIES = {k: v for k, v in QUERIES.items() if not k.startswith("_")}

if not QUERIES:
    sys.exit(f"{QUERIES_FILE} contains no queries.")

TRUNCATE = 6000
SOFT_BOOST = 0.05

# ---------------------------------------------------------------
# Embedding: same call as the original scripts, with a cache added
# ---------------------------------------------------------------

_cache = {}
if os.path.exists(CACHE_FILE):
    try:
        _cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        print(f"loaded {len(_cache)} cached embeddings")
    except Exception:
        _cache = {}

_new_since_save = 0


def embed(text):
    global _new_since_save
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]

    if MOCK:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [((h[i % len(h)] + i * 7) % 256) / 255.0 - 0.5 for i in range(64)]
    else:
        import requests
        r = requests.post(OLLAMA_EMBED,
                          json={"model": "bge-m3", "prompt": text[:TRUNCATE],
                                "options": {"num_ctx": 8192}},
                          timeout=300)
        data = r.json()
        if "embedding" not in data:
            r = requests.post(OLLAMA_EMBED,
                              json={"model": "bge-m3", "prompt": text[:2500],
                                    "options": {"num_ctx": 8192}},
                              timeout=300)
            data = r.json()
            if "embedding" not in data:
                raise RuntimeError(f"Ollama error: {data}")
        vec = data["embedding"]

    _cache[key] = vec
    _new_since_save += 1
    if _new_since_save >= 20:
        save_cache()
    return vec


def save_cache():
    global _new_since_save
    json.dump(_cache, open(CACHE_FILE, "w", encoding="utf-8"))
    _new_since_save = 0


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------
# Intent detection: identical to run_metadata_rag.py, unmodified.
# The rules match on Chinese keywords, so a test set written in
# another language will not trigger them.
# ---------------------------------------------------------------

def detect_intent(query):
    q = query
    if any(k in q for k in ['決定', '已決定', '確定要']):
        return (['Decided', 'Implemented'], True)
    if any(k in q for k in ['放棄', '不做', '不投', '淘汰']):
        return (['Abandoned'], True)
    if any(k in q for k in ['還要', '還需要', '現在要']):
        return (['Decided', 'Implemented', 'Abandoned'], False)
    if any(k in q for k in ['考慮過', '評估過', '想過']):
        return (['Exploring', 'Decided'], False)
    if any(k in q for k in ['為什麼', '是什麼', '什麼意思']):
        return (['Informational'], False)
    return (None, False)


# ---------------------------------------------------------------
# Configurations
#   embed_notes   prepend notes to the embedded text
#   embed_status  prepend decision_status to the embedded text
#   filter_mode   off / soft / as_is (as_is keeps the original hard and soft split)
#   expand        enable related_segments expansion
# ---------------------------------------------------------------

CONFIGS = [
    ("A_baseline",        dict(embed_notes=False, embed_status=False, filter_mode="off",   expand=False)),
    ("B_full",            dict(embed_notes=True,  embed_status=True,  filter_mode="as_is", expand=True)),
    ("C_filter_only",     dict(embed_notes=False, embed_status=False, filter_mode="as_is", expand=False)),
    ("D_embed_only",      dict(embed_notes=True,  embed_status=True,  filter_mode="off",   expand=False)),
    ("E_no_expand",       dict(embed_notes=True,  embed_status=True,  filter_mode="as_is", expand=False)),
    ("F_notes_only",      dict(embed_notes=True,  embed_status=False, filter_mode="off",   expand=False)),
    ("G_status_only",     dict(embed_notes=False, embed_status=True,  filter_mode="off",   expand=False)),
    ("H_all_soft",        dict(embed_notes=True,  embed_status=True,  filter_mode="soft",  expand=False)),
    ("I_filter_only_soft", dict(embed_notes=False, embed_status=False, filter_mode="soft", expand=False)),
    ("J_expand_only",     dict(embed_notes=False, embed_status=False, filter_mode="off",   expand=True)),
]

DESCRIPTIONS = {
    "A_baseline": "Baseline: plain text embedding, no filtering, no expansion",
    "B_full": "Full system: all three mechanisms enabled",
    "C_filter_only": "Filtering only; no metadata in the embedded text",
    "D_embed_only": "Metadata in the embedded text only; no filtering",
    "E_no_expand": "Full system with relation expansion disabled. Identical to B means expansion contributes nothing",
    "F_notes_only": "Embedding prepends notes only",
    "G_status_only": "Embedding prepends decision_status only",
    "H_all_soft": "Hard filter downgraded to a soft score boost; otherwise as E",
    "I_filter_only_soft": "Soft filtering only",
    "J_expand_only": "Relation expansion only",
}


def build_embed_text(seg, cfg):
    prefix = ""
    if cfg["embed_notes"] and seg.get("notes"):
        prefix += f"【決策紀錄】{seg['notes']}\n"
    if cfg["embed_status"]:
        prefix += f"【狀態】{seg.get('decision_status', '')}\n"
    if prefix:
        prefix += "\n"
    return prefix + seg["text"]


def run_config(name, cfg, corpus):
    seg_by_id = {s["segment_id"]: s for s in corpus}
    vectors = {s["segment_id"]: embed(build_embed_text(s, cfg)) for s in corpus}

    out, tp, tr = {}, 0.0, 0.0
    for q, gt in QUERIES.items():
        qv = embed(q)
        statuses, hard = detect_intent(q)
        if cfg["filter_mode"] == "off":
            statuses, hard = None, False
        elif cfg["filter_mode"] == "soft":
            hard = False

        cands = []
        for s in corpus:
            sim = cosine(qv, vectors[s["segment_id"]])
            st = s.get("decision_status", "")
            if statuses and hard:
                if st not in statuses:
                    continue
            elif statuses and st in statuses:
                sim += SOFT_BOOST
            cands.append((sim, s))

        cands.sort(key=lambda x: x[0], reverse=True)
        top5 = [s["segment_id"] for _, s in cands[:5]]

        if cfg["expand"]:
            for _, s in cands[:3]:
                for rid in s.get("related_segments", []):
                    if rid in seg_by_id and rid not in top5 and len(top5) < 5:
                        top5.append(rid)
            top5 = top5[:5]

        hits = [sid for sid in top5 if sid in gt]
        p, r = len(hits) / 5, len(hits) / len(gt)
        tp += p
        tr += r
        out[q] = {"top5": top5, "ground_truth": gt, "hits": hits,
                  "n_hits": len(hits), "precision@5": p, "recall@5": r,
                  "intent_filter": statuses, "hard_filter": hard}

    n = len(QUERIES)
    return {"config": name, "settings": cfg, "description": DESCRIPTIONS[name],
            "mean_precision@5": tp / n, "mean_recall@5": tr / n,
            "total_hits": sum(v["n_hits"] for v in out.values()),
            "per_query": out}


def diagnostics(corpus):
    print("\n=== diagnostics ===")
    n = len(corpus)
    print(f"corpus: {n} records")
    for f in ["notes", "decision_status", "related_segments", "maturity",
              "importance", "valid_from", "prerequisites", "L1_codes"]:
        filled = sum(1 for s in corpus if s.get(f))
        print(f"  {f:<20} {filled}/{n} populated")

    print(f"\ntruncation risk (embedding limit {TRUNCATE} characters)")
    for label, cfg in [("plain text", CONFIGS[0][1]), ("with metadata", CONFIGS[1][1])]:
        over = [s["segment_id"] for s in corpus
                if len(build_embed_text(s, cfg)) > TRUNCATE]
        print(f"  {label}: {len(over)} over the limit {over[:8]}")
    lost = []
    for s in corpus:
        plain = build_embed_text(s, CONFIGS[0][1])
        rich = build_embed_text(s, CONFIGS[1][1])
        if len(rich) > TRUNCATE and len(plain) <= TRUNCATE:
            lost.append(s["segment_id"])
        elif len(rich) > TRUNCATE:
            extra = len(rich) - len(plain)
            if extra > 0:
                lost.append(s["segment_id"])
    print(f"  records losing original text because of the prefix: "
          f"{len(set(lost))} {sorted(set(lost))[:8]}")

    print("\nintent rule firing")
    fired = 0
    for q in QUERIES:
        st, hard = detect_intent(q)
        label = q.split()[0]
        if st:
            fired += 1
            print(f"  {label:<4} -> {'+'.join(st)} ({'hard' if hard else 'soft'})")
        else:
            print(f"  {label:<4} -> no rule fired")
    print(f"  {fired} of {len(QUERIES)} questions fired a rule. The rules were "
          f"written with the questions already known, so their effect may be overstated.")


def significance(base, other):
    try:
        from scipy.stats import wilcoxon
    except ImportError:
        return None
    a = [v["recall@5"] for v in base["per_query"].values()]
    b = [v["recall@5"] for v in other["per_query"].values()]
    if all(x == y for x, y in zip(a, b)):
        return None
    try:
        return wilcoxon(a, b, zero_method="wilcox", alternative="less").pvalue
    except ValueError:
        return None


def main():
    if not os.path.exists(CORPUS_FILE):
        sys.exit(f"{CORPUS_FILE} not found. cd into the project folder first.")
    corpus = json.load(open(CORPUS_FILE, encoding="utf-8"))
    diagnostics(corpus)

    try:
        import scipy  # noqa: F401
    except ImportError:
        print("\n[scipy is not installed. The p column will be empty. "
              "Install it with: pip install scipy]")

    if MOCK:
        print("\n[MOCK mode: fake vectors, scores are meaningless, "
              "this only verifies that the pipeline runs]")

    results = {}
    for name, cfg in CONFIGS:
        print(f"\nrunning {name} ...", flush=True)
        results[name] = run_config(name, cfg, corpus)
        r = results[name]
        print(f"  P@5={r['mean_precision@5']:.4f}  R@5={r['mean_recall@5']:.4f}  "
              f"hits={r['total_hits']}/{sum(len(v) for v in QUERIES.values())}")
    save_cache()

    base = results["A_baseline"]
    b_r = base["mean_recall@5"]
    total_gt = sum(len(v) for v in QUERIES.values())

    lines = ["# Ablation results", "",
             f"Corpus of {len(corpus)} records, test set of {len(QUERIES)} questions, "
             f"{total_gt} relevance judgements in total.", "",
             "| Configuration | Description | P@5 | R@5 | vs baseline | Hits | p |",
             "|---|---|---|---|---|---|---|"]
    print("\n" + "=" * 78)
    print(f"{'configuration':<20}{'P@5':>8}{'R@5':>8}{'vs base':>12}{'hits':>8}")
    print("=" * 78)
    for name, _ in CONFIGS:
        r = results[name]
        delta = (r["mean_recall@5"] / b_r - 1) * 100 if b_r else float("nan")
        p = significance(base, r)
        ptxt = f"{p:.3f}" if p is not None else "-"
        print(f"{name:<20}{r['mean_precision@5']:>8.4f}{r['mean_recall@5']:>8.4f}"
              f"{delta:>11.1f}%{r['total_hits']:>8}")
        lines.append(f"| {name} | {r['description']} | {r['mean_precision@5']:.4f} | "
                     f"{r['mean_recall@5']:.4f} | {delta:+.1f}% | "
                     f"{r['total_hits']}/{total_gt} | {ptxt} |")
    print("=" * 78)

    lines += ["", "## Hits per question (the raw numerator behind Recall@5)", "",
              "| Configuration | " + " | ".join(q.split()[0] for q in QUERIES) + " |",
              "|---" * (len(QUERIES) + 1) + "|"]
    for name, _ in CONFIGS:
        r = results[name]
        cells = [str(v["n_hits"]) for v in r["per_query"].values()]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += ["", "A percentage change can come from a single hit on one question. "
                  "Read the table above alongside it."]

    json.dump(results, open("ablation_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    open("ablation_table.md", "w", encoding="utf-8").write("\n".join(lines))
    print("\nwrote ablation_results.json and ablation_table.md")


if __name__ == "__main__":
    main()
