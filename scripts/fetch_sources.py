#!/usr/bin/env python3
"""
Generate the input CSVs for search_log.py from public APIs. Standard library only.

  python fetch_sources.py ieee YOUR_IEEE_API_KEY   -> ieee.csv      (IEEE Xplore API, needs the key you applied for)
  python fetch_sources.py openalex                 -> openalex.csv  (OpenAlex, no key; stands in for Google Scholar)
  python fetch_sources.py chase                    -> chase.csv     (citation chasing from the four seed papers, via OpenAlex)

Then:  python search_log.py merge ieee.csv openalex.csv chase.csv

Why OpenAlex and not Google Scholar: Scholar has no API, and automated scraping breaks its terms and gets
blocked. If you use OpenAlex, say "OpenAlex" instead of "Google Scholar" in the Literature search paragraph
and in Table 2 (or run Scholar by hand in Publish or Perish and use that CSV instead).
"""
import csv, json, sys, time, urllib.error, urllib.parse, urllib.request

MAILTO = "syamasudha.v@vit.ac.in"            # OpenAlex 'polite pool'
FROM, TO = "2023-01-01", "2026-09-30"
OPENALEX_CAP = 1000                           # max records kept from OpenAlex (report this number in the paper)

# Same terms as the manuscript
IEEE_QUERY = ('("diffusion" OR "score based" OR "score-based" OR "flow matching" OR "rectified flow" OR "Schrodinger bridge") AND ("semantic communication" OR "semantic communications" OR "joint source-channel coding" OR "JSCC" OR "wireless image")')

# Seed papers for citation chasing (the first OpenAlex hit is printed so you can check it).
# If a hit is wrong, put the OpenAlex work id (e.g. "W1234567890") in place of the title.
SEEDS = ["CDDM: Channel Denoising Diffusion Models for Wireless Semantic Communications",
         "Generative AI Meets 6G and Beyond: Diffusion Models for Semantic Communications",
         "ICDM: Interference Cancellation Diffusion Models for Wireless Semantic Communications",
         "Land-then-transport: A Flow Matching-Based Generative Decoder for Wireless Image Transmission"]


def get_json(url, tries=8):
    req = urllib.request.Request(url, headers={"User-Agent": f"lit-review/1.0 (mailto:{MAILTO})"})
    for i in range(1, tries + 1):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            if i == tries or e.code not in (429, 500, 502, 503, 504):
                raise
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:      # timeouts, SSL handshake, DNS
            if i == tries:
                print("\nCould not reach the server. Check your internet, turn off any VPN, "
                      "or try another network (e.g. a phone hotspot).")
                raise
            err = f"connection problem ({type(e).__name__})"
        wait = 10 * i
        print(f"  {err}; retry {i}/{tries} in {wait}s ...", flush=True)
        time.sleep(wait)


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title", "year", "doi", "arxiv_id", "abstract"])
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {len(rows)} rows to {path}")


# ------------------------------------------------------------------ IEEE Xplore
def cmd_ieee(key):
    base = "https://ieeexploreapi.ieee.org/api/v1/search/articles?"
    rows, start, total = [], 1, None
    while total is None or start <= total:
        q = urllib.parse.urlencode({"apikey": key, "querytext": IEEE_QUERY, "start_year": 2023, "end_year": 2026,
                                    "max_records": 200, "start_record": start, "sort_field": "publication_year"})
        d = get_json(base + q)
        total = int(d.get("total_records", 0))
        arts = d.get("articles", [])
        if not arts:
            break
        for a in arts:
            rows.append({"title": a.get("title", ""), "year": a.get("publication_year", ""),
                         "doi": a.get("doi", ""), "arxiv_id": "", "abstract": a.get("abstract", "")})
        start += 200
        time.sleep(1)
    print(f"IEEE Xplore: total_records = {total}")
    write_csv("ieee.csv", rows)


# ------------------------------------------------------------------ OpenAlex helpers
def abstract_text(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def work_row(w):
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    return {"title": (w.get("title") or w.get("display_name") or "").strip(),
            "year": w.get("publication_year") or "", "doi": doi, "arxiv_id": "",
            "abstract": abstract_text(w.get("abstract_inverted_index"))}


def paged(url_base, params, cap=None):
    rows, cursor, total = [], "*", None
    while cursor:
        d = get_json(url_base + urllib.parse.urlencode({**params, "per-page": 200, "cursor": cursor, "mailto": MAILTO}))
        total = d["meta"]["count"]
        rows += [work_row(w) for w in d["results"]]
        cursor = d["meta"].get("next_cursor")
        if cap and len(rows) >= cap:
            rows = rows[:cap]
            break
        time.sleep(0.2)
    return rows, total


# ------------------------------------------------------------------ OpenAlex search (Scholar stand-in)
def cmd_openalex():
    q = IEEE_QUERY
    flt = f"title_and_abstract.search:{q},from_publication_date:{FROM},to_publication_date:{TO}"
    rows, total = paged("https://api.openalex.org/works?", {"filter": flt}, cap=OPENALEX_CAP)
    print(f"OpenAlex: matching records = {total}; kept {len(rows)} (cap {OPENALEX_CAP})")
    write_csv("openalex.csv", rows)


# ------------------------------------------------------------------ citation chasing
def find_seed(s):
    if s.upper().startswith("W") and s[1:].isdigit():
        return get_json(f"https://api.openalex.org/works/{s}?mailto={MAILTO}")
    d = get_json("https://api.openalex.org/works?" + urllib.parse.urlencode({"search": s, "per-page": 1, "mailto": MAILTO}))
    return d["results"][0] if d["results"] else None


def cmd_chase():
    rows, seen = [], set()
    for s in SEEDS:
        w = find_seed(s)
        if not w:
            print(f"NOT FOUND: {s}")
            continue
        wid = w["id"].rsplit("/", 1)[-1]
        print(f"Seed: {w['display_name']} ({w.get('publication_year')}) [{wid}]  <- check this is the right paper")
        # forward: papers citing the seed, within the date window
        fwd, n = paged("https://api.openalex.org/works?",
                       {"filter": f"cites:{wid},from_publication_date:{FROM},to_publication_date:{TO}"})
        # backward: papers the seed cites, restricted to the same window
        refs = [r.rsplit("/", 1)[-1] for r in w.get("referenced_works", [])]
        bwd = []
        for i in range(0, len(refs), 50):
            batch = "|".join(refs[i:i + 50])
            part, _ = paged("https://api.openalex.org/works?",
                            {"filter": f"openalex:{batch},from_publication_date:{FROM},to_publication_date:{TO}"})
            bwd += part
        print(f"  forward {len(fwd)}, backward {len(bwd)} (in {FROM[:4]}-{TO[:4]})")
        for r in fwd + bwd:
            k = (r["doi"] or r["title"]).lower()
            if r["title"] and k not in seen:
                seen.add(k)
                rows.append(r)
    write_csv("chase.csv", rows)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "ieee" and len(sys.argv) == 3:
        cmd_ieee(sys.argv[2])
    elif c == "openalex":
        cmd_openalex()
    elif c == "chase":
        cmd_chase()
    else:
        print(__doc__)
