import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from docx import Document
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "all-MiniLM-L6-v2"

# Load model once at module level so it's not reloaded per campaign
print("  Loading sentence-transformers model...")
_model = SentenceTransformer(MODEL_NAME)
print("  Model loaded.")


def extract_cv_text(cv_path: str) -> str:
    """Extract plain text from a .docx CV file."""
    if not os.path.exists(cv_path):
        raise FileNotFoundError(
            f"CV not found at: {cv_path}\n"
            f"Please place your CV at this exact path."
        )
    doc        = Document(cv_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    cv_text    = " ".join(paragraphs)

    if not cv_text:
        raise ValueError(f"CV at {cv_path} appears empty — check the file.")

    print(f"  CV loaded: {len(cv_text)} characters, {len(paragraphs)} paragraphs")
    return cv_text


def score_jobs(df: pd.DataFrame, cv_text: str) -> pd.DataFrame:
    """
    Compute cosine similarity between the CV and each job.
    Combines title + description for richer matching.
    Adds match_score column to DataFrame.
    """
    # Encode CV once
    cv_embedding = _model.encode([cv_text], show_progress_bar=False)

    # Combine title + description for each job — richer signal than description alone
    job_texts    = (df["title"] + " " + df["description"]).tolist()
    job_embeddings = _model.encode(
        job_texts,
        show_progress_bar=True,
        batch_size=16,
    )

    scores        = cosine_similarity(cv_embedding, job_embeddings)[0]
    df            = df.copy()
    df["match_score"] = np.round(scores, 4)
    return df


def run_matcher(cleaned_results: dict) -> dict:
    """
    Score all jobs in each campaign against the campaign's assigned CV.
    Input:  dict of {campaign_name: clean_df}
    Output: dict of {campaign_name: scored_df} — only jobs above threshold
    """
    from config import CAMPAIGNS
    print("\n=== MODULE 3: CV matching and scoring ===")

    scored_results = {}

    # Cache CV embeddings so same CV isn't re-read for multiple campaigns
    cv_cache = {}

    for campaign_name, df in cleaned_results.items():
        campaign  = CAMPAIGNS.get(campaign_name, {})
        campaign["name"] = campaign_name
        cv_path   = campaign.get("cv", "")
        threshold = campaign.get("match_threshold", 0.50)

        print(f"\n  [{campaign_name}]")
        print(f"  CV: {cv_path}")
        print(f"  Threshold: {threshold}")
        print(f"  Jobs to score: {len(df)}")

        if df.empty:
            print(f"  No jobs to score — skipping")
            continue

        # Load CV text (cached)
        if cv_path not in cv_cache:
            try:
                cv_cache[cv_path] = extract_cv_text(cv_path)
            except (FileNotFoundError, ValueError) as e:
                print(f"  ERROR: {e}")
                continue

        cv_text = cv_cache[cv_path]

        # Score all jobs
        df = score_jobs(df, cv_text)

        # Sort by score descending
        df = df.sort_values("match_score", ascending=False).reset_index(drop=True)

        # Show score breakdown
        print(f"\n  Score breakdown for [{campaign_name}]:")
        for _, row in df.iterrows():
            bar    = "█" * int(row["match_score"] * 20)
            status = "✓ PASS" if row["match_score"] >= threshold else "✗ DROP"
            print(f"    {status} {row['match_score']:.3f} {bar:<20} "
                  f"{row['title'][:35]:<35} @ {row['company'][:20]}")

        # Filter by threshold
        before = len(df)
        df     = df[df["match_score"] >= threshold].reset_index(drop=True)
        print(f"\n  Dropped {before - len(df)} below threshold — "
              f"{len(df)} quality matches remaining")

        if not df.empty:
            scored_results[campaign_name] = df

    total = sum(len(df) for df in scored_results.values())
    print(f"\n=== Module 3 complete — {total} quality matches across "
          f"{len(scored_results)} campaigns ===")
    return scored_results


if __name__ == "__main__":
    from modules.scraper import run_scraper
    from modules.cleaner import run_cleaner

    scraped = run_scraper()
    cleaned = run_cleaner(scraped)
    scored  = run_matcher(cleaned)

    print("\n--- Top matches per campaign ---")
    for campaign_name, df in scored.items():
        print(f"\n[{campaign_name}]")
        for _, row in df.iterrows():
            print(f"  {row['match_score']:.3f}  {row['title']} @ {row['company']}")
            print(f"           {row['url']}")

    total = sum(len(df) for df in scored.values())
    print(f"\n✓ Module 3 test complete — {total} quality matches ready for Module 4")