from __future__ import annotations

import argparse
import csv
import io
import re
import time
from dataclasses import dataclass, asdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

MARKET_SNAPSHOT = DATA / "market_snapshot.csv"
RAW = DATA / "fundamentals_raw.csv"
SOURCES = DATA / "fundamental_sources.csv"
REVIEW = DATA / "fundamentals_review_queue.csv"

CMA_ROOT = "https://annualreport.cma.or.ke/"
USER_AGENT = (
    "NSE-Insight/2.0 (+private research dashboard; "
    "low-frequency official-source fundamentals updater)"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

RAW_COLUMNS = [
    "ticker","financial_period","source_name","source_type","source_url","verified_on",
    "eps","book_value_per_share","profit_after_tax","prior_profit_after_tax",
    "revenue","prior_revenue","total_equity","prior_total_equity","ebit","finance_cost",
    "roe_pct","net_margin_pct","interest_cover","dividend_per_share","dividend_years",
    "payout_ratio_pct","earnings_growth_pct","revenue_growth_pct","governance_flag",
]

SOURCE_COLUMNS = [
    "ticker","company","sector","match_status","match_score","cma_company",
    "cma_company_page","report_year","report_url","checked_on","notes",
]

REVIEW_COLUMNS = RAW_COLUMNS + [
    "company","match_score","extraction_confidence","extraction_notes",
]


ALIASES = {
    "absa bank kenya": "barclays bank",
    "british american investments": "britam holdings",
    "imh holdings": "i&m holdings",
    "hfcb group": "housing finance",
    "kenya commercial bank": "kenya commercial bank",
    "co operative bank of kenya": "co-operative bank of kenya",
    "total kenya": "total kenya",
    "b o c kenya": "boc kenya",
    "nairobi securities exchange": "nairobi securities exchange",
    "east african breweries": "east african breweries",
    "kenya power lighting": "kenya power",
    "british american tobacco kenya": "british american tobacco kenya",
}


STOPWORDS = {
    "plc","ltd","limited","holdings","group","ord","ordinary","company","co",
    "the","kenya","k","0rd","shares","share","issuer"
}


def _get(url: str, timeout: int = 30) -> requests.Response:
    last = None
    for attempt in range(3):
        try:
            response = SESSION.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last


def normalize_company_name(value: str) -> str:
    s = str(value or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\bord(?:\.)?\s*\d+(?:\.\d+)?\b", " ", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", " ", s)
    s = re.sub(r"[^a-z0-9&]+", " ", s)
    tokens = [t for t in s.split() if t not in STOPWORDS]
    return " ".join(tokens).strip()


def alias_target(company: str) -> str:
    norm = normalize_company_name(company)
    for source, target in ALIASES.items():
        if source in norm or norm in source:
            return normalize_company_name(target)
    return norm


def similarity(a: str, b: str) -> float:
    a = alias_target(a)
    b = normalize_company_name(b)
    if not a or not b:
        return 0.0

    seq = SequenceMatcher(None, a, b).ratio()
    at = set(a.split())
    bt = set(b.split())
    overlap = len(at & bt) / max(1, len(at | bt))
    containment = 1.0 if (a in b or b in a) else 0.0
    return round((0.58 * seq + 0.32 * overlap + 0.10 * containment) * 100, 1)


@dataclass
class CmaCompany:
    name: str
    category: str
    page_url: str


@dataclass
class ReportCandidate:
    year: int
    url: str
    label: str


def crawl_cma_companies() -> list[CmaCompany]:
    root = BeautifulSoup(_get(CMA_ROOT).text, "html.parser")
    categories = []
    for a in root.find_all("a", href=True):
        href = urljoin(CMA_ROOT, a["href"])
        if "/business/" in href:
            categories.append((a.get_text(" ", strip=True), href))

    # Preserve order while deduplicating.
    seen = set()
    deduped = []
    for name, href in categories:
        if href not in seen:
            seen.add(href)
            deduped.append((name, href))

    companies: list[CmaCompany] = []
    for category_name, category_url in deduped:
        try:
            soup = BeautifulSoup(_get(category_url).text, "html.parser")
        except requests.RequestException:
            continue

        for a in soup.find_all("a", href=True):
            href = urljoin(category_url, a["href"])
            name = a.get_text(" ", strip=True)
            if "/company/" in href and name:
                companies.append(CmaCompany(name=name, category=category_name, page_url=href))

    unique = {}
    for c in companies:
        unique[c.page_url] = c
    return list(unique.values())


def find_reports(company_page: str) -> list[ReportCandidate]:
    soup = BeautifulSoup(_get(company_page).text, "html.parser")
    found: dict[str, ReportCandidate] = {}

    # Direct PDF anchors are ideal.
    for a in soup.find_all("a", href=True):
        href = urljoin(company_page, a["href"])
        text = a.get_text(" ", strip=True)
        haystack = f"{text} {href}"
        year_match = re.search(r"\b(20\d{2})\b", haystack)
        if ".pdf" in href.lower() and year_match:
            year = int(year_match.group(1))
            found[href] = ReportCandidate(year=year, url=href, label=text)

    # Some CMA pages expose title links that then resolve to PDFs.
    if not found:
        anchors = soup.find_all("a", href=True)
        for a in anchors:
            text = a.get_text(" ", strip=True)
            year_match = re.search(r"\b(20\d{2})\b", text)
            if not year_match:
                continue
            href = urljoin(company_page, a["href"])
            if "download" in text.lower() or "view" in text.lower() or "pdf" in text.lower():
                found[href] = ReportCandidate(
                    year=int(year_match.group(1)),
                    url=href,
                    label=text,
                )

    return sorted(found.values(), key=lambda r: (r.year, r.url), reverse=True)


def best_match(market_name: str, companies: list[CmaCompany]) -> tuple[CmaCompany | None, float]:
    scored = [(c, similarity(market_name, c.name)) for c in companies]
    if not scored:
        return None, 0.0
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0]


NUMBER = r"[-(]?\d[\d,]*(?:\.\d+)?\)?"

PATTERNS = {
    "eps": [
        rf"(?:basic\s+)?earnings\s+per\s+share(?:\s*\([^)]*\))?\s*[:\-]?\s*({NUMBER})",
        rf"eps\s*[:\-]?\s*({NUMBER})",
    ],
    "dividend_per_share": [
        rf"(?:total\s+)?dividend\s+per\s+(?:ordinary\s+)?share(?:\s*\([^)]*\))?\s*[:\-]?\s*({NUMBER})",
        rf"dividend\s+per\s+share\s*[:\-]?\s*({NUMBER})",
    ],
    "roe_pct": [
        rf"return\s+on\s+(?:average\s+)?equity(?:\s*\(%\))?\s*[:\-]?\s*({NUMBER})",
        rf"\broe(?:\s*\(%\))?\s*[:\-]?\s*({NUMBER})",
    ],
    "net_margin_pct": [
        rf"net\s+profit\s+margin(?:\s*\(%\))?\s*[:\-]?\s*({NUMBER})",
    ],
    "earnings_growth_pct": [
        rf"(?:profit|earnings)\s+growth(?:\s*\(%\))?\s*[:\-]?\s*({NUMBER})",
    ],
    "revenue_growth_pct": [
        rf"revenue\s+growth(?:\s*\(%\))?\s*[:\-]?\s*({NUMBER})",
    ],
}

TABLE_PATTERNS = {
    "profit_after_tax": [
        "profit after tax",
        "profit for the year",
        "profit after taxation",
        "profit attributable to owners",
    ],
    "revenue": [
        "revenue",
        "total income",
        "operating income",
    ],
    "total_equity": [
        "total equity",
        "shareholders' equity",
        "equity attributable to owners",
    ],
    "ebit": [
        "operating profit",
        "profit from operations",
        "earnings before interest and tax",
    ],
    "finance_cost": [
        "finance costs",
        "finance cost",
    ],
}


def _number(value: str):
    s = str(value or "").strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace(",", "").replace("(", "").replace(")", "")
    try:
        value = float(s)
    except ValueError:
        return None
    if negative:
        value = -value
    return value


def _extract_pdf_text(pdf_bytes: bytes, max_pages: int = 180) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    chunks = []
    for page in reader.pages[:max_pages]:
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _single_metric(text: str, metric: str):
    for pattern in PATTERNS.get(metric, []):
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        value = _number(match.group(1))
        if value is None:
            continue
        # Guardrails for per-share/percentage values.
        if metric in {"eps", "dividend_per_share"} and not (-1000 < value < 10000):
            continue
        if metric.endswith("_pct") and not (-500 < value < 500):
            continue
        return value
    return None


def _line_metric(
    text: str,
    labels: list[str],
) -> tuple[float | None, float | None]:
    """
    Extract current and comparative values from financial statement rows.

    Labels must begin the row so that lines such as
    'Revenue growth (%) 9.5' are not treated as Revenue.
    """

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
    ]

    for line in lines:
        low = line.lower()

        matched_label = None

        for label in labels:
            pattern = rf"^\s*{re.escape(label)}\b"

            if re.search(pattern, low):
                matched_label = label
                break

        if matched_label is None:
            continue

        remainder = line[len(matched_label):].strip()

        if remainder.lower().startswith(
            ("growth", "margin", "per share", "ratio")
        ):
            continue

        values = re.findall(NUMBER, remainder)

        nums = [_number(v) for v in values]
        nums = [v for v in nums if v is not None]

        nums = [
            v
            for v in nums
            if not (
                1900 <= abs(v) <= 2100
                and float(v).is_integer()
            )
        ]

        if not nums:
            continue

        current = nums[0]
        prior = nums[1] if len(nums) > 1 else None

        return current, prior

    return None, None


def extract_candidates(text: str) -> tuple[dict, str, int]:
    clean = text.replace("\u00a0", " ")
    record = {c: "" for c in RAW_COLUMNS}
    notes = []
    points = 0

    for metric in PATTERNS:
        value = _single_metric(clean, metric)
        if value is not None:
            record[metric] = value
            points += 2
        else:
            notes.append(f"{metric}:not-found")

    pairs = {
        "profit_after_tax": "prior_profit_after_tax",
        "revenue": "prior_revenue",
        "total_equity": "prior_total_equity",
    }
    for metric, labels in TABLE_PATTERNS.items():
        current, prior = _line_metric(clean, labels)
        if current is not None:
            record[metric] = current
            points += 1
            if metric in pairs and prior is not None:
                record[pairs[metric]] = prior
                points += 1
        else:
            notes.append(f"{metric}:not-found")

    # Confidence is deliberately conservative.
    # 8+ = enough independently extracted fields for automatic acceptance.
    if points >= 10:
        confidence = "HIGH"
    elif points >= 6:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return record, confidence, points


def load_existing_raw() -> pd.DataFrame:
    if not RAW.exists() or RAW.stat().st_size == 0:
        return pd.DataFrame(columns=RAW_COLUMNS)
    df = pd.read_csv(RAW)
    for col in RAW_COLUMNS:
        if col not in df:
            df[col] = ""
    return df[RAW_COLUMNS]


def merge_raw(existing: pd.DataFrame, accepted: list[dict]) -> pd.DataFrame:
    if not accepted:
        return existing

    incoming = pd.DataFrame(accepted)
    for col in RAW_COLUMNS:
        if col not in incoming:
            incoming[col] = ""
    incoming = incoming[RAW_COLUMNS]

    combined = pd.concat([existing, incoming], ignore_index=True)
    combined["_period_sort"] = combined["financial_period"].astype(str)
    combined = combined.sort_values(["ticker", "_period_sort"])
    combined = combined.drop_duplicates(["ticker", "financial_period"], keep="last")
    return combined.drop(columns="_period_sort")


def run(max_companies: int | None = None, discover_only: bool = False, min_match: float = 52.0):
    if not MARKET_SNAPSHOT.exists():
        raise FileNotFoundError("data/market_snapshot.csv does not exist")

    market = pd.read_csv(MARKET_SNAPSHOT)
    market = market[["ticker","company","sector"]].drop_duplicates("ticker")
    if max_companies:
        market = market.head(max_companies)

    cma_companies = crawl_cma_companies()
    if not cma_companies:
        raise RuntimeError("CMA resource portal returned no company pages")

    source_rows = []
    review_rows = []
    accepted = []

    for _, security in market.iterrows():
        ticker = str(security["ticker"]).strip()
        company = str(security["company"]).strip()
        sector = str(security["sector"]).strip()

        cma, score = best_match(company, cma_companies)
        source = {
            "ticker": ticker,
            "company": company,
            "sector": sector,
            "match_status": "UNMATCHED",
            "match_score": score,
            "cma_company": cma.name if cma else "",
            "cma_company_page": cma.page_url if cma else "",
            "report_year": "",
            "report_url": "",
            "checked_on": date.today().isoformat(),
            "notes": "",
        }

        if not cma or score < min_match:
            source["notes"] = "No sufficiently strong CMA company match"
            source_rows.append(source)
            continue

        source["match_status"] = "MATCHED"

        try:
            reports = find_reports(cma.page_url)
        except requests.RequestException as exc:
            source["notes"] = f"Company page unavailable: {exc}"
            source_rows.append(source)
            continue

        if not reports:
            source["notes"] = "No direct PDF report discovered"
            source_rows.append(source)
            continue

        latest = reports[0]
        source["report_year"] = latest.year
        source["report_url"] = latest.url

        if discover_only:
            source_rows.append(source)
            continue

        try:
            response = _get(latest.url, timeout=60)
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not latest.url.lower().endswith(".pdf"):
                source["notes"] = "Latest report link did not resolve directly to a PDF"
                source_rows.append(source)
                continue

            text = _extract_pdf_text(response.content)
        except Exception as exc:
            source["notes"] = f"PDF extraction failed: {type(exc).__name__}"
            source_rows.append(source)
            continue

        if len(text.strip()) < 1000:
            source["notes"] = "PDF has little/no extractable text; possible scanned report"
            source_rows.append(source)
            continue

        extracted, confidence, points = extract_candidates(text)
        row = {c: extracted.get(c, "") for c in RAW_COLUMNS}
        row.update({
            "ticker": ticker,
            "financial_period": f"FY{latest.year}",
            "source_name": f"{cma.name} {latest.year} annual report",
            "source_type": "CMA-hosted annual report",
            "source_url": latest.url,
            "verified_on": date.today().isoformat(),
            "governance_flag": 0,
        })

        # Existing manually verified data should not be displaced by weak extraction.
        if confidence == "HIGH":
            accepted.append(row)
            source["notes"] = f"Auto-accepted extraction ({points} confidence points)"
        else:
            review = dict(row)
            review.update({
                "company": company,
                "match_score": score,
                "extraction_confidence": confidence,
                "extraction_notes": f"{points} confidence points; manual review before acceptance",
            })
            review_rows.append(review)
            source["notes"] = f"Sent to review queue ({confidence}; {points} points)"

        source_rows.append(source)

    pd.DataFrame(source_rows, columns=SOURCE_COLUMNS).to_csv(SOURCES, index=False)

    if review_rows:
        pd.DataFrame(review_rows, columns=REVIEW_COLUMNS).to_csv(REVIEW, index=False)
    else:
        pd.DataFrame(columns=REVIEW_COLUMNS).to_csv(REVIEW, index=False)

    existing = load_existing_raw()
    merged = merge_raw(existing, accepted)
    merged.to_csv(RAW, index=False)

    # Rebuild ratios only if the repository already has the builder.
    try:
        from build_fundamentals import build_fundamentals
        build_fundamentals()
    except Exception as exc:
        print(f"Fundamentals ratio rebuild skipped: {exc}")

    summary = pd.Series([r["match_status"] for r in source_rows]).value_counts().to_dict()
    print(
        f"Checked {len(source_rows)} securities. "
        f"Matched {summary.get('MATCHED', 0)}; "
        f"unmatched {summary.get('UNMATCHED', 0)}; "
        f"auto-accepted {len(accepted)}; review queue {len(review_rows)}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Discover CMA annual reports and safely update NSE Insight fundamentals."
    )
    parser.add_argument("--max-companies", type=int, default=None)
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--min-match", type=float, default=52.0)
    args = parser.parse_args()

    run(
        max_companies=args.max_companies,
        discover_only=args.discover_only,
        min_match=args.min_match,
    )


if __name__ == "__main__":
    main()
