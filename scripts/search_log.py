#!/usr/bin/env python3
"""
Search log helper for the literature-selection table (Table 2).

Four commands, run in this order:

  1. python search_log.py arxiv                  -> arxiv.csv  (+ prints the raw arXiv count)
  2. python search_log.py merge ieee.csv scholar.csv chase.csv
                                                  -> screening.csv (+ prints identified / dedup counts)
  3. (you) open screening.csv and fill the three decision columns
  4. python search_log.py tally                  -> prints all counts, checks them, writes table2.tex

Input files for step 2 (any CSV with a title column; DOI, year and abstract columns are used if present):
  ieee.csv     IEEE Xplore: Export -> CSV
  scholar.csv  Google Scholar hits, e.g. from Publish or Perish -> Save results as CSV
  chase.csv    citation chasing: one row per reference/citing paper (title, doi, year)
Duplicates are matched on DOI, arXiv ID, exact normalized title, or the first 30 characters of the
normalized title (this catches a preprint and its journal version when the title was extended).
Skim screening.csv for any remaining duplicates and delete the extra row before screening.
Use "-" in place of a file name to skip a source (its count is then 0).
"""
import csv, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------- protocol (edit here, then keep it fixed)
START, END = "202301010000", "202609302359"          # Jan 2023 - Sep 2026
ARXIV_QUERY = (
    '(all:"diffusion" OR all:"score based" OR all:"score-based" OR all:"flow matching" OR all:"rectified flow" OR all:"Schrodinger bridge") AND (all:"semantic communication" OR all:"semantic communications" OR all:"joint source-channel coding" OR all:"JSCC" OR all:"wireless image")'
)
SOURCE_ORDER = ["ieee", "arxiv", "scholar", "chase"]
TITLE_ABS_OK = {"include", "exclude"}
FULLTEXT_OK = {"include", "exclude", "discussed"}
REASONS = {"larger_system": "diffusion only inside a larger generative system, no noise mitigation role",
           "no_comparable": "no comparable formulation or evaluation",
           "other": "other"}


# ---------------------------------------------------------------- helpers
def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def arxiv_id(*texts):
    for t in texts:
        m = re.search(r"(?:arxiv[:./ ]*)?(\d{4}\.\d{4,5})(?:v\d+)?", t or "", re.I)
        if m:
            return m.group(1)
    return ""


def pick(row, *names):
    low = {k.lower().strip(): v for k, v in row.items() if k}
    for n in names:
        for k, v in low.items():
            if n in k and v:
                return v.strip()
    return ""


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- step 1: arXiv
def fetch(url, tries=8):
    """GET with a User-Agent and retries (arXiv answers 503 when busy; networks may time out)."""
    req = urllib.request.Request(url, headers={"User-Agent": "lit-review-search-log/1.0 (mailto:syamasudha.v@vit.ac.in)"})
    for i in range(1, tries + 1):
        wait = 15 * i
        try:
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After") if e.headers else None
            if ra and ra.isdigit():
                wait = max(wait, int(ra))
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            err = f"connection problem ({type(e).__name__})"
        if i == tries:
            raise SystemExit("Could not reach the server. Check your internet, turn off any VPN, "
                             "or try another network (e.g. a phone hotspot).")
        print(f"  {err}; retry {i}/{tries} in {wait}s ...", flush=True)
        time.sleep(wait)


def cmd_arxiv():
    base = "https://export.arxiv.org/api/query?"
    q = f"{ARXIV_QUERY} AND submittedDate:[{START} TO {END}]"
    ns = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}
    rows, start, total = [], 0, None
    while total is None or start < total:
        url = base + urllib.parse.urlencode(
            {"search_query": q, "start": start, "max_results": 200, "sortBy": "submittedDate"})
        root = ET.fromstring(fetch(url))
        total = int(root.find("o:totalResults", ns).text)
        for e in root.findall("a:entry", ns):
            aid = e.find("a:id", ns).text
            rows.append({"title": " ".join(e.find("a:title", ns).text.split()),
                         "year": e.find("a:published", ns).text[:4],
                         "doi": "", "arxiv_id": arxiv_id(aid),
                         "abstract": " ".join(e.find("a:summary", ns).text.split())})
        start += 200
        time.sleep(3)                                 # arXiv API etiquette
    write_csv("arxiv.csv", rows, ["title", "year", "doi", "arxiv_id", "abstract"])
    print(f"arXiv: totalResults = {total}, saved {len(rows)} rows to arxiv.csv")
    print("Query used:", q)


# ---------------------------------------------------------------- step 2: merge
def load_source(name, path):
    if path == "-":
        return []
    if not os.path.exists(path):
        print(f"  (skipping {name}: {path} not found)")
        return []
    out = []
    for r in read_csv(path):
        title = pick(r, "document title", "title")
        if not title:
            continue
        doi = norm_doi(pick(r, "doi"))
        out.append({"title": title, "year": pick(r, "year"), "doi": doi,
                    "arxiv_id": pick(r, "arxiv_id") or arxiv_id(pick(r, "url", "link"), title),
                    "abstract": pick(r, "abstract"), "source": name})
    return out


def cmd_merge(paths):
    srcs = dict(zip(["ieee", "scholar", "chase"], paths))
    srcs["arxiv"] = "arxiv.csv"
    raw = {n: load_source(n, srcs.get(n, "-")) for n in SOURCE_ORDER}
    merged, index = [], {}                            # index: key -> merged record
    for n in SOURCE_ORDER:
        for r in raw[n]:
            nt = norm_title(r["title"])
            keys = [k for k in (("doi", r["doi"]), ("arx", r["arxiv_id"]), ("t", nt),
                                ("p", nt[:30] if len(nt) >= 30 else "")) if k[1]]
            hit = next((index[k] for k in keys if k in index), None)
            if hit is None:
                hit = {"title": r["title"], "year": r["year"], "doi": r["doi"], "arxiv_id": r["arxiv_id"],
                       "abstract": r["abstract"], "sources": set()}
                merged.append(hit)
            hit["sources"].add(n)
            for f in ("doi", "arxiv_id", "abstract", "year"):
                hit[f] = hit[f] or r[f]
            for k in keys:
                index[k] = hit
    rows = []
    for i, m in enumerate(merged, 1):
        rows.append({"id": i, "title": m["title"], "year": m["year"], "doi": m["doi"], "arxiv_id": m["arxiv_id"],
                     "sources": "+".join(s for s in SOURCE_ORDER if s in m["sources"]),
                     "title_abs_decision": "", "fulltext_decision": "", "reason": "", "abstract": m["abstract"]})
    write_csv("screening.csv", rows, ["id", "title", "year", "doi", "arxiv_id", "sources",
                                      "title_abs_decision", "fulltext_decision", "reason", "abstract"])
    print("Raw records identified per source:")
    for n in SOURCE_ORDER:
        print(f"  {n:8s} {len(raw[n])}")
    print(f"Records after removing duplicates: {len(rows)}")
    only_chase = sum(1 for r in rows if r["sources"] == "chase")
    print(f"  of which found only by citation chasing: {only_chase}")
    print("Wrote screening.csv. Fill title_abs_decision (include/exclude), fulltext_decision "
          "(include/exclude/discussed) and reason, then run: python search_log.py tally")


# ---------------------------------------------------------------- optional: rank rows to speed up screening
GROUPS = [("diffusion", "score-based", "score based", "flow matching", "flow-matching", "denoising diffusion", "generative"),
          ("semantic communication", "semantic communications", "jscc", "joint source-channel", "joint source channel"),
          ("wireless", "channel", "snr", "fading", "awgn", "mimo", "ofdm"),
          ("denois", "interference", "posterior sampling", "inverse problem", "adversarial", "jamming", "robust")]


def cmd_rank():
    """Adds keyword_score (0-4: how many topic groups appear in title+abstract) and sorts high to low.
    It only changes the ORDER. It never fills a decision column."""
    rows = read_csv("screening.csv")
    for r in rows:
        text = (r["title"] + " " + r.get("abstract", "")).lower()
        r["keyword_score"] = sum(any(k in text for k in g) for g in GROUPS)
    rows.sort(key=lambda r: (-int(r["keyword_score"]), int(r["id"])))
    fields = ["id", "keyword_score", "title", "year", "doi", "arxiv_id", "sources",
              "title_abs_decision", "fulltext_decision", "reason", "abstract"]
    write_csv("screening.csv", rows, fields)
    from collections import Counter
    c = Counter(int(r["keyword_score"]) for r in rows)
    print("keyword_score counts:", {k: c[k] for k in sorted(c, reverse=True)})
    print("screening.csv re-sorted (highest score first). Decisions are still yours.")


# ---------------------------------------------------------------- accept reviewed suggestions / list PDFs needed
def cmd_accept(path="screening_suggested.csv"):
    """Copies the reviewed 'suggested' column into title_abs_decision and writes screening.csv.
    Refuses while any row is still 'maybe' or empty. fulltext_decision is left blank on purpose:
    it must come from reading the full text."""
    rows = read_csv(path)
    bad = [r["id"] for r in rows if r["suggested"].strip().lower() not in TITLE_ABS_OK]
    if bad:
        print(f"{len(bad)} rows are still not include/exclude (e.g. ids {bad[:15]}). Resolve them in {path} first.")
        sys.exit(1)
    for r in rows:
        r["title_abs_decision"] = r["suggested"].strip().lower()
        r["fulltext_decision"] = r.get("fulltext_decision", "")
        r["reason"] = ""
    fields = ["id", "keyword_score", "title", "year", "doi", "arxiv_id", "sources",
              "title_abs_decision", "fulltext_decision", "reason", "abstract"]
    write_csv("screening.csv", [{k: r.get(k, "") for k in fields} for r in rows], fields)
    n = sum(r["title_abs_decision"] == "include" for r in rows)
    print(f"Wrote screening.csv: {n} included and {len(rows) - n} excluded at title/abstract.")


def cmd_needpdf():
    rows = [r for r in read_csv("screening.csv") if r["title_abs_decision"].strip().lower() == "include"]
    have = [r for r in rows if r["arxiv_id"].strip()]
    need = [r for r in rows if not r["arxiv_id"].strip()]
    write_csv("needpdf.csv", need, ["id", "title", "year", "doi", "sources"] if False else list(need[0].keys()) if need else ["id"])
    print(f"{len(rows)} included: {len(have)} have an arXiv id (I can read them), {len(need)} do not.")
    print("Wrote needpdf.csv: download these as PDFs (named <id>.pdf) and upload them.")


# ---------------------------------------------------------------- step 4: tally
def cmd_tally():
    rows = read_csv("screening.csv")
    n_dedup = len(rows)
    bad = []
    n_ta_ex = n_ft = n_ft_ex = n_inc = n_disc = 0
    reasons = {k: 0 for k in REASONS}
    for r in rows:
        ta, ft, why = (r["title_abs_decision"].strip().lower(), r["fulltext_decision"].strip().lower(),
                       r["reason"].strip().lower())
        if ta not in TITLE_ABS_OK:
            bad.append((r["id"], "title_abs_decision empty or invalid")); continue
        if ta == "exclude":
            n_ta_ex += 1; continue
        n_ft += 1
        if ft not in FULLTEXT_OK:
            bad.append((r["id"], "fulltext_decision empty or invalid")); continue
        if ft == "include":
            n_inc += 1
        else:
            n_ft_ex += 1
            if ft == "discussed":
                n_disc += 1
            else:
                if why not in REASONS:
                    bad.append((r["id"], f"reason must be one of {sorted(REASONS)}")); continue
                reasons[why] += 1
    if bad:
        print(f"{len(bad)} of {n_dedup} rows still need a valid decision (first 50 shown):")
        for i, m in bad[:50]:
            print(f"  id {i}: {m}")
        sys.exit(1)
    src = {n: 0 for n in SOURCE_ORDER}
    for r in rows:                                    # first-listed source = where it was first identified
        src[r["sources"].split("+")[0]] = src.get(r["sources"].split("+")[0], 0) + 1
    print(f"After removing duplicates      {n_dedup}")
    print(f"Excluded at title/abstract     {n_ta_ex}")
    print(f"Full texts assessed            {n_ft}")
    print(f"Excluded at full text          {n_ft_ex}  (discussed but not counted: {n_disc}; reasons: {reasons})")
    print(f"Included                       {n_inc}")
    ok = (n_dedup - n_ta_ex == n_ft) and (n_ft - n_ft_ex == n_inc)
    print("Arithmetic check:", "OK" if ok else "FAILED")
    if n_inc != 151 or n_disc != 2:
        print(f"WARNING: manuscript says 151 included and 2 discussed; you have {n_inc} and {n_disc}. "
              "Either fix the decisions or change the numbers in the text.")
    print("Raw source counts are printed by the merge step; copy them into the table below.")
    tex = (r"""\begin{table}[t]
\centering
\caption{Literature search and selection (flow of records).}\label{tab:prisma}
\small
\begin{tabularx}{\textwidth}{@{}l r X@{}}
\toprule
Stage & Records & Notes\\
\midrule
Identified: IEEE Xplore & RAW_ieee & query terms in the text, Jan 2023--Sep 2026\\
Identified: arXiv & RAW_arxiv & same terms, all fields\\
Identified: OpenAlex & RAW_scholar & same terms, title and abstract fields, first 1000 records\\
Identified: citation chasing & RAW_chase & backward and forward from \cite{cddm,qin25,icdm,ltt}\\
After removing duplicates & %d & preprint and journal versions merged\\
Excluded at title/abstract screening & %d & no diffusion or flow based generative model, or no wireless pipeline\\
Full texts assessed & %d & \\
Excluded at full text & %d & diffusion only inside a larger generative system with no noise mitigation role (%d), no comparable formulation or evaluation (%d), other (%d), discussed but not counted (%d, \sref{sec:commin})\\
\textbf{Included (Table~\ref{tab:taxonomy})} & \textbf{%d} & \\
\bottomrule
\end{tabularx}
\legend{This is a structured narrative review and not a PRISMA style systematic review.}
\end{table}
""" % (n_dedup, n_ta_ex, n_ft, n_ft_ex, reasons["larger_system"], reasons["no_comparable"],
       reasons["other"], n_disc, n_inc))
    open("table2.tex", "w", encoding="utf-8").write(tex)
    print("Wrote table2.tex (replace RAW_* with the raw counts printed by the merge step).")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "arxiv":
        cmd_arxiv()
    elif c == "merge" and len(sys.argv) == 5:
        cmd_merge(sys.argv[2:5])
    elif c == "accept":
        cmd_accept()
    elif c == "needpdf":
        cmd_needpdf()
    elif c == "rank":
        cmd_rank()
    elif c == "tally":
        cmd_tally()
    else:
        print(__doc__)
