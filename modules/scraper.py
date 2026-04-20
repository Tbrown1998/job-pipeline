import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
from apify_client import ApifyClient
from config import APIFY_API_TOKEN, SOURCES, REMOTE_KEYWORDS, EXCLUDE_KEYWORDS


def is_remote(job: dict) -> bool:
    """Lightweight remote check at scrape time. Cleaner does the strict pass."""
    combined = " ".join([
        job.get("title", ""),
        job.get("location", ""),
        job.get("description", "")[:500],
    ]).lower()
    has_remote    = any(kw in combined for kw in REMOTE_KEYWORDS)
    has_exclusion = any(kw in combined for kw in EXCLUDE_KEYWORDS)
    return has_remote and not has_exclusion


def passes_location_filter(job: dict, campaign: dict) -> bool:
    """
    For remote_only campaigns — job must pass remote check.
    For non-remote campaigns (Nigeria/Africa) — accept everything scraped.
    """
    if campaign.get("remote_only", False):
        return is_remote(job)
    return True   # hybrid and onsite allowed for local campaigns


def scrape_linkedin(client: ApifyClient, campaign: dict) -> list[dict]:
    if not SOURCES.get("linkedin", {}).get("enabled"):
        return []
    if "linkedin" not in campaign.get("sources", []):
        return []

    actor    = SOURCES["linkedin"]["actor"]
    all_jobs = []

    base_url = (
        "https://www.linkedin.com/jobs/search/"
        "?keywords={query}&location={location}&sortBy=DD"
    )
    # Add remote filter param only for remote_only campaigns
    if campaign.get("remote_only", False):
        base_url += "&f_WT=2"

    urls = [
        base_url.format(
            query=kw.replace(" ", "%20"),
            location=loc.replace(" ", "%20"),
        )
        for kw  in campaign["keywords"]
        for loc in campaign["locations"]
    ]

    print(f"  LinkedIn: {len(urls)} URLs ({len(campaign['keywords'])} keywords × {len(campaign['locations'])} locations)...")
    try:
        run   = client.actor(actor).call(run_input={
            "urls":       urls,
            "maxResults": len(urls) * 8,
        })
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        kept  = []
        for item in items:
            job = {
                "title":       item.get("title", ""),
                "company":     item.get("companyName", ""),
                "location":    item.get("location", ""),
                "description": item.get("description", ""),
                "url":         item.get("jobUrl", ""),
                "date_posted": item.get("postedAt", ""),
                "source":      "LinkedIn",
                "campaign":    campaign["name"],
            }
            if passes_location_filter(job, campaign):
                kept.append(job)
        all_jobs.extend(kept)
        print(f"    -> {len(items)} scraped, {len(kept)} passed location filter")
    except Exception as e:
        print(f"    -> LinkedIn failed: {e}")

    return all_jobs


def scrape_indeed(client: ApifyClient, campaign: dict) -> list[dict]:
    if not SOURCES.get("indeed", {}).get("enabled"):
        return []
    if "indeed" not in campaign.get("sources", []):
        return []

    actor    = SOURCES["indeed"]["actor"]
    all_jobs = []

    for kw in campaign["keywords"]:
        for code in campaign["country_codes"]:
            # Pass location=remote for remote_only campaigns
            location = "remote" if campaign.get("remote_only", False) else ""
            print(f"  Indeed: '{kw}' in {code} {'(remote)' if location else ''}...")
            try:
                run   = client.actor(actor).call(run_input={
                    "position": kw,
                    "country":  code,
                    "location": location,
                    "maxItems": 10,
                })
                items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
                kept  = []
                for item in items:
                    job = {
                        "title":       item.get("positionName", ""),
                        "company":     item.get("company", ""),
                        "location":    item.get("location", ""),
                        "description": item.get("description", ""),
                        "url":         item.get("url", ""),
                        "date_posted": item.get("datePosted", ""),
                        "source":      "Indeed",
                        "campaign":    campaign["name"],
                    }
                    if passes_location_filter(job, campaign):
                        kept.append(job)
                all_jobs.extend(kept)
                print(f"    -> {len(items)} scraped, {len(kept)} passed filter")
            except Exception as e:
                print(f"    -> Indeed failed '{kw}' / {code}: {e}")

    return all_jobs


def scrape_remotive(campaign: dict) -> list[dict]:
    if not SOURCES.get("remotive", {}).get("enabled"):
        return []
    if "remotive" not in campaign.get("sources", []):
        return []

    all_jobs = []

    # Use remotive_keywords if defined, otherwise fall back to roles
    search_terms = campaign.get("remotive_keywords", campaign.get("roles", []))

    for term in search_terms:
        print(f"  Remotive: '{term}'...")
        try:
            response = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": term, "limit": 10},
                timeout=15,
            )
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
            for item in jobs:
                all_jobs.append({
                    "title":       item.get("title", ""),
                    "company":     item.get("company_name", ""),
                    "location":    item.get("candidate_required_location", "Remote"),
                    "description": item.get("description", ""),
                    "url":         item.get("url", ""),
                    "date_posted": item.get("publication_date", ""),
                    "source":      "Remotive",
                    "campaign":    campaign["name"],
                })
            print(f"    -> {len(jobs)} found")
        except Exception as e:
            print(f"    -> Remotive failed '{term}': {e}")

    return all_jobs


def scrape_remoteok(campaign: dict) -> list[dict]:
    """Remote OK — free API, good for remote tech/data roles. No key needed."""
    if not SOURCES.get("remoteok", {}).get("enabled"):
        return []
    if "remoteok" not in campaign.get("sources", []):
        return []

    all_jobs = []
    search_terms = campaign.get("remotive_keywords", campaign.get("roles", []))

    for term in search_terms:
        print(f"  RemoteOK: '{term}'...")
        try:
            response = requests.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "JobPipeline/1.0"},
                timeout=15,
            )
            response.raise_for_status()
            jobs = response.json()

            # First item is metadata, skip it
            if isinstance(jobs, list) and len(jobs) > 1:
                jobs = jobs[1:]

            kept = []
            for item in jobs:
                title = item.get("position", "")
                desc  = item.get("description", "")
                combined = (title + " " + desc[:300]).lower()

                # Only keep jobs that match the search term
                if term.lower().split()[0] not in combined:
                    continue

                job = {
                    "title":       title,
                    "company":     item.get("company", ""),
                    "location":    item.get("location", "Remote"),
                    "description": desc,
                    "url":         item.get("url", ""),
                    "date_posted": item.get("date", ""),
                    "source":      "RemoteOK",
                    "campaign":    campaign["name"],
                }
                if passes_location_filter(job, campaign):
                    kept.append(job)

                if len(kept) >= 10:
                    break

            all_jobs.extend(kept)
            print(f"    -> {len(kept)} relevant jobs found")
        except Exception as e:
            print(f"    -> RemoteOK failed '{term}': {e}")

    return all_jobs


def scrape_arbeitnow(campaign: dict) -> list[dict]:
    """
    Arbeitnow — free job board API, strong for remote and EU roles.
    No API key needed.
    """
    if not SOURCES.get("arbeitnow", {}).get("enabled"):
        return []
    if "arbeitnow" not in campaign.get("sources", []):
        return []

    all_jobs = []

    for kw in campaign["keywords"]:
        print(f"  Arbeitnow: '{kw}'...")
        try:
            response = requests.get(
                "https://arbeitnow.com/api/job-board-api",
                params={"search": kw, "page": 1},
                timeout=15,
            )
            response.raise_for_status()
            jobs = response.json().get("data", [])
            kept = []
            for item in jobs:
                job = {
                    "title":       item.get("title", ""),
                    "company":     item.get("company_name", ""),
                    "location":    item.get("location", "Remote"),
                    "description": item.get("description", ""),
                    "url":         item.get("url", ""),
                    "date_posted": item.get("created_at", ""),
                    "source":      "Arbeitnow",
                    "campaign":    campaign["name"],
                }
                if passes_location_filter(job, campaign):
                    kept.append(job)
            all_jobs.extend(kept)
            print(f"    -> {len(jobs)} found, {len(kept)} passed filter")
        except Exception as e:
            print(f"    -> Arbeitnow failed '{kw}': {e}")

    return all_jobs


def scrape_themuse(campaign: dict) -> list[dict]:
    if not SOURCES.get("themuse", {}).get("enabled"):
        return []
    if "themuse" not in campaign.get("sources", []):
        return []

    all_jobs = []
    seen_urls = set()

    # The Muse categories relevant to your roles
    categories = ["Data Science", "IT", "Software Engineer"]

    print(f"  The Muse: scanning relevant categories...")
    try:
        for category in categories:
            for page in range(0, 3):   # 3 pages = ~60 jobs per category
                response = requests.get(
                    "https://www.themuse.com/api/public/jobs",
                    params={"category": category, "page": page},
                    timeout=15,
                )
                response.raise_for_status()
                jobs = response.json().get("results", [])
                if not jobs:
                    break

                for item in jobs:
                    url = item.get("refs", {}).get("landing_page", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    locations = item.get("locations", [])
                    location  = locations[0].get("name", "") if locations else ""
                    title     = item.get("name", "")
                    contents  = item.get("contents", "")

                    # Filter by relevance to campaign roles
                    combined = (title + " " + contents[:500]).lower()
                    role_match = any(
                        role.lower().split()[0] in combined
                        for role in campaign["roles"]
                    )
                    if not role_match:
                        continue

                    job = {
                        "title":       title,
                        "company":     item.get("company", {}).get("name", ""),
                        "location":    location,
                        "description": contents,
                        "url":         url,
                        "date_posted": item.get("publication_date", ""),
                        "source":      "TheMuse",
                        "campaign":    campaign["name"],
                    }
                    if passes_location_filter(job, campaign):
                        all_jobs.append(job)

        print(f"    -> {len(all_jobs)} relevant jobs found")
    except Exception as e:
        print(f"    -> The Muse failed: {e}")

    return all_jobs


def scrape_apify_generic(client: ApifyClient, source_key: str, campaign: dict) -> list[dict]:
    """
    Generic handler for any Apify-based source that accepts
    keyword + location inputs (wellfound, weworkremotely, jobberman etc).
    Falls back gracefully if Actor input schema differs.
    """
    source = SOURCES.get(source_key, {})
    if not source.get("enabled"):
        return []
    if source_key not in campaign.get("sources", []):
        return []

    actor    = source["actor"]
    all_jobs = []

    for kw in campaign["keywords"]:
        print(f"  {source_key.title()}: '{kw}'...")
        try:
            run   = client.actor(actor).call(run_input={
                "query":    kw,
                "location": campaign["locations"][0],
                "maxItems": 10,
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            kept  = []
            for item in items:
                job = {
                    "title":       item.get("title", item.get("positionName", "")),
                    "company":     item.get("company", item.get("companyName", "")),
                    "location":    item.get("location", ""),
                    "description": item.get("description", ""),
                    "url":         item.get("url", item.get("jobUrl", "")),
                    "date_posted": item.get("datePosted", item.get("postedAt", "")),
                    "source":      source_key.title(),
                    "campaign":    campaign["name"],
                }
                if passes_location_filter(job, campaign):
                    kept.append(job)
            all_jobs.extend(kept)
            print(f"    -> {len(items)} scraped, {len(kept)} passed filter")
        except Exception as e:
            print(f"    -> {source_key.title()} failed '{kw}': {e}")

    return all_jobs


def run_scraper_for_campaign(campaign: dict) -> pd.DataFrame:
    """Run all enabled sources for a single campaign."""
    print(f"\n  [{campaign['name']}] {campaign['description']}")
    client   = ApifyClient(APIFY_API_TOKEN)
    all_jobs = []

    # Dedicated scrapers
    all_jobs.extend(scrape_linkedin(client, campaign))
    all_jobs.extend(scrape_indeed(client, campaign))
    all_jobs.extend(scrape_remotive(campaign))
    all_jobs.extend(scrape_remoteok(campaign))

    # Generic Apify sources
    for source_key in ["weworkremotely", "wellfound", "jobberman", "myjobmag"]:
        all_jobs.extend(scrape_apify_generic(client, source_key, campaign))

    df = pd.DataFrame(all_jobs) if all_jobs else pd.DataFrame()
    print(f"\n  Raw jobs collected for [{campaign['name']}]: {len(df)}")
    return df


def run_scraper(campaign_name: str = None) -> dict:
    """
    Run scraper for all enabled campaigns or one specific campaign.
    Returns dict of {campaign_name: DataFrame}.
    """
    from config import CAMPAIGNS
    print("\n=== MODULE 1: Scraping jobs ===")

    results = {}

    for name, campaign in CAMPAIGNS.items():
        if not campaign.get("enabled", False):
            print(f"\n  [{name}] Skipped — disabled")
            continue
        if campaign_name and name != campaign_name:
            continue

        campaign["name"] = name
        df = run_scraper_for_campaign(campaign)
        if not df.empty:
            results[name] = df

    total = sum(len(df) for df in results.values())
    print(f"\n=== Module 1 complete — {total} total raw jobs across {len(results)} campaigns ===")
    return results


if __name__ == "__main__":
    results = run_scraper()

    for cname, df in results.items():
        print(f"\n{'─'*55}")
        print(f"Campaign: {cname} — {len(df)} jobs")
        print(f"{'─'*55}")
        for _, row in df.head(3).iterrows():
            print(f"  {row['title']} @ {row['company']}")
            print(f"  Source: {row['source']} | Location: {row['location']}")
            print(f"  URL: {row['url'][:80]}")

    print(f"\n✓ Module 1 test complete")