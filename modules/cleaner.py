import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import REMOTE_KEYWORDS, EXCLUDE_KEYWORDS


def strip_html(text: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_genuinely_remote(job: dict, campaign: dict) -> bool:
    """
    For remote_only campaigns — strict check, job must signal remote
    in title or location field, not just buried in description.
    For non-remote campaigns (Nigeria/Africa) — accept everything.
    """
    if not campaign.get("remote_only", False):
        return True

    title    = job.get("title", "").lower()
    location = job.get("location", "").lower()
    desc     = job.get("description", "").lower()[:300]

    # Strong signal — remote in title or location
    strong_remote = any(kw in title or kw in location for kw in REMOTE_KEYWORDS)

    # Weak signal — remote only in description
    weak_remote = any(kw in desc for kw in REMOTE_KEYWORDS)

    # Exclusion — hybrid or onsite language in title or location
    exclusion_words = [
        "hybrid", "on-site", "onsite", "office based",
        "in office", "in-office", "on site only", "no remote",
    ]
    has_exclusion = any(kw in title or kw in location for kw in exclusion_words)

    if has_exclusion:
        return False
    return strong_remote or weak_remote


def passes_language_filter(job: dict) -> bool:
    """Drop jobs requiring non-English languages."""
    combined = " ".join([
        job.get("title", ""),
        job.get("description", "")[:1000],
    ]).lower()

    disqualifying = [
        "fluent in spanish", "spanish speaker", "spanish-speaking",
        "native spanish", "spanish language required",
        "fluent in french", "french speaker", "french-speaking",
        "native french", "french language required",
        "fluent in portuguese", "portuguese speaker",
        "fluent in arabic", "arabic speaker",
        "fluent in german", "german speaker",
        "bilingual spanish", "bilingual french",
    ]
    return not any(phrase in combined for phrase in disqualifying)


def passes_geographic_filter(job: dict, campaign: dict) -> bool:
    """Drop jobs restricted to specific non-African locations."""
    if campaign.get("remote_only", False):
        return True

    title    = job.get("title", "").lower()
    location = job.get("location", "").lower()
    desc     = job.get("description", "")[:800].lower()
    combined = title + " " + location + " " + desc

    # Location field itself says a non-African country
    location_exclusions = [
        "united states", "united kingdom", "canada", "australia",
        "germany", "france", "spain", "netherlands", "sweden",
        "usa", "uk,", " uk ", "new york", "san francisco",
        "london", "berlin", "toronto", "sydney", "singapore",
    ]
    if any(phrase in location for phrase in location_exclusions):
        return False

    # Description says explicitly restricted
    desc_exclusions = [
        "us only", "usa only", "united states only",
        "must be based in the us", "must be based in us",
        "must reside in the us", "us residents only", "us citizens only",
        "uk only", "united kingdom only", "must be based in the uk",
        "must be uk based", "uk residents only",
        "canada only", "australia only",
        "authorized to work in the us",
        "authorized to work in the united states",
        "right to work in the uk",
        "eu only", "european union only",
    ]
    return not any(phrase in combined for phrase in desc_exclusions)


def filter_by_date(df: pd.DataFrame, max_age_hours: int) -> pd.DataFrame:
    """Remove jobs older than max_age_hours. Keep jobs with unparseable dates."""
    if max_age_hours <= 0:
        return df

    before  = len(df)
    cutoff  = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    date_formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d %B %Y",
        "%B %d, %Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S+00:00",   # ← add this
        "%Y-%m-%d %H:%M:%S",          # ← and this
    ]

    def is_recent(date_str) -> bool:
        if not date_str or str(date_str).strip() == "":
            return True   # no date — keep it
        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return dt >= cutoff
            except ValueError:
                continue
        return True   # unparseable — keep it

    df = df[df["date_posted"].apply(is_recent)].reset_index(drop=True)
    after = len(df)
    if before - after > 0:
        print(f"  Old jobs removed: {before - after} ({before} → {after}, cutoff: {max_age_hours}hrs)")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Two-pass deduplication:
    1. Exact URL match
    2. Same company + normalised title (catches same job on different boards)
    """
    before = len(df)

    # Pass 1 — exact URL
    df = df.drop_duplicates(subset=["url"], keep="first")

    # Pass 2 — company + title
    df = df.copy()
    df["_title_norm"]   = df["title"].str.lower().str.strip()
    df["_company_norm"] = df["company"].str.lower().str.strip()
    df = df.drop_duplicates(subset=["_company_norm", "_title_norm"], keep="first")
    df = df.drop(columns=["_title_norm", "_company_norm"])

    after = len(df)
    print(f"  Duplicates removed: {before - after} ({before} → {after})")
    return df.reset_index(drop=True)


def remove_already_seen(df: pd.DataFrame, tracker_path: str) -> pd.DataFrame:
    """Skip jobs whose URLs already exist in the Excel tracker."""
    if not os.path.exists(tracker_path):
        print("  Tracker not found — skipping seen filter (first run)")
        return df

    before = len(df)
    try:
        existing  = pd.read_excel(tracker_path, usecols=["url"])
        seen_urls = set(existing["url"].dropna().tolist())
        df        = df[~df["url"].isin(seen_urls)].reset_index(drop=True)
        after     = len(df)
        print(f"  Already seen removed: {before - after} ({before} → {after})")
    except Exception as e:
        print(f"  Could not read tracker — skipping seen filter: {e}")

    return df


def clean_campaign(df: pd.DataFrame, campaign: dict,
                   tracker_path: str = "data/job_tracker.xlsx") -> pd.DataFrame:
    """
    Run all cleaning steps for a single campaign's DataFrame.
    Returns cleaned DataFrame ready for scoring.
    """
    campaign_name = campaign.get("name", "unknown")
    print(f"\n  Cleaning [{campaign_name}] — {len(df)} raw jobs")

    if df.empty:
        print(f"  No jobs to clean for [{campaign_name}]")
        return df

    # Step 1 — strip HTML from descriptions
    df["description"] = df["description"].apply(strip_html)

    # Step 2 — drop empty titles or companies
    before = len(df)
    df = df[df["title"].str.strip() != ""]
    df = df[df["company"].str.strip() != ""]
    if before - len(df) > 0:
        print(f"  Empty fields removed: {before - len(df)}")

    # Step 3 — date filter using campaign's max_age_hours
    df = filter_by_date(df, campaign.get("max_age_hours", 48))

    # Step 4 — strict remote filter for remote_only campaigns
    before = len(df)
    df = df[df.apply(lambda row: is_genuinely_remote(row, campaign), axis=1)]
    df = df.reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"  Non-remote removed: {removed} ({before} → {len(df)})")

    # Step 4b — language filter
    before = len(df)
    df = df[df.apply(passes_language_filter, axis=1)].reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"  Non-English language jobs removed: {removed}")

    # Step 4c — geographic restriction filter
    before = len(df)
    df = df[df.apply(lambda row: passes_geographic_filter(row, campaign), axis=1)].reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"  Geographically restricted jobs removed: {removed}")

    if df.empty:
        print(f"  No jobs remaining after filters for [{campaign_name}]")
        return df

    # Step 5 — deduplicate within this campaign
    if df.empty:
        print(f"  No jobs remaining after filters for [{campaign_name}]")
        return df
    df = remove_duplicates(df)

    # Step 6 — remove jobs already in tracker
    if df.empty:
        return df
    df = remove_already_seen(df, tracker_path)

    print(f"  Clean jobs ready for scoring [{campaign_name}]: {len(df)}")
    return df.reset_index(drop=True)


def run_cleaner(scraped_results: dict,
                tracker_path: str = "data/job_tracker.xlsx") -> dict:
    """
    Run cleaner across all campaign DataFrames.
    Input:  dict of {campaign_name: raw_df}
    Output: dict of {campaign_name: clean_df}
    """
    from config import CAMPAIGNS
    print("\n=== MODULE 2: Cleaning and deduplicating ===")

    cleaned_results = {}

    for campaign_name, df in scraped_results.items():
        # Get the full campaign config so we can pass it down
        campaign = CAMPAIGNS.get(campaign_name, {})
        campaign["name"] = campaign_name

        clean_df = clean_campaign(df, campaign, tracker_path)

        if not clean_df.empty:
            cleaned_results[campaign_name] = clean_df

    total = sum(len(df) for df in cleaned_results.values())
    print(f"\n=== Module 2 complete — {total} clean jobs across {len(cleaned_results)} campaigns ===")
    return cleaned_results


if __name__ == "__main__":
    from modules.scraper import run_scraper

    scraped  = run_scraper()
    cleaned  = run_cleaner(scraped)

    print("\n--- Sample cleaned output ---")
    for campaign_name, df in cleaned.items():
        print(f"\n[{campaign_name}] — {len(df)} clean jobs")
        for _, row in df.head(3).iterrows():
            print(f"  {row['title']} @ {row['company']}")
            print(f"  Source: {row['source']} | Location: {row['location']}")

    total = sum(len(df) for df in cleaned.values())
    print(f"\n✓ Module 2 test complete — {total} clean jobs ready for Module 3")