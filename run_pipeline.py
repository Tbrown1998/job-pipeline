import sys
import os
import argparse
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run(campaign_name: str = None, skip_tailor: bool = False,
        skip_alert: bool = False):
    """Run the full pipeline."""
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"  JOB PIPELINE — {start.strftime('%A %d %B %Y %H:%M')}")
    print(f"{'='*60}")

    # Module 1 — Scrape
    from modules.scraper import run_scraper
    scraped = run_scraper(campaign_name)

    if not scraped:
        print("\n  No jobs scraped — pipeline stopping early.")
        return

    # Module 2 — Clean
    from modules.cleaner import run_cleaner
    cleaned = run_cleaner(scraped)

    if not cleaned:
        print("\n  No jobs after cleaning — pipeline stopping early.")
        return

    # Module 3 — Score
    from modules.matcher import run_matcher
    scored = run_matcher(cleaned)

    if not scored:
        print("\n  No jobs above threshold — pipeline stopping early.")
        return

    # Module 4 — Tailor (optional skip for speed)
    if skip_tailor:
        print("\n  Skipping Module 4 (tailoring) — --skip-tailor flag set")
        tailored = scored
    else:
        from modules.tailor import run_tailor
        tailored = run_tailor(scored)

    # Module 5 — Track
    from modules.tracker import run_tracker
    run_tracker(tailored)

    # Module 6 — Alert (optional skip)
    if skip_alert:
        print("\n  Skipping Module 6 (alert) — --skip-alert flag set")
    else:
        from modules.alerter import run_alerter
        run_alerter(tailored)

    # Summary
    elapsed = datetime.now() - start
    total   = sum(len(df) for df in tailored.values())
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Jobs matched:  {total}")
    print(f"  Campaigns run: {len(tailored)}")
    print(f"  Time elapsed:  {elapsed}")
    print(f"  Tracker:       {os.path.abspath('data/job_tracker.xlsx')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the job search pipeline")
    parser.add_argument("--campaign", type=str, default=None,
                        help="Run a specific campaign only")
    parser.add_argument("--skip-tailor", action="store_true",
                        help="Skip cover letter / ATS answer generation")
    parser.add_argument("--skip-alert", action="store_true",
                        help="Skip email digest alert")
    args = parser.parse_args()

    run(campaign_name=args.campaign,
        skip_tailor=args.skip_tailor,
        skip_alert=args.skip_alert)