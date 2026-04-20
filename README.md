# Job Search Pipeline

An automated job search pipeline built in Python that finds, scores, tailors, tracks, and alerts you to quality job opportunities across multiple job boards. Designed for targeted, quality-matched applications rather than volume spam.

## What it does

The pipeline runs daily (manually or scheduled) and performs six steps:

1. **Scrapes** job listings from LinkedIn, Indeed, Jobberman, MyJobMag, Remotive, RemoteOK, and more
2. **Cleans** raw results by stripping HTML, removing duplicates across boards, filtering by language, geography, and date
3. **Scores** each job against your CV using semantic similarity (sentence-transformers + cosine similarity) so only genuinely relevant roles get through
4. **Generates** a tailored cover letter and pre-filled ATS answers for each matched job using Claude AI
5. **Tracks** every matched job in an Excel spreadsheet with status tracking, match scores, and file paths
6. **Sends** a daily email digest with your top new matches so you know exactly where to apply each morning

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    run_pipeline.py                       │
│                 (orchestrates everything)                │
└──────────┬──────────────────────────────────────────────┘
           │
           ▼
┌──────────────────┐     ┌──────────────────┐
│  Module 1        │     │  config.py       │
│  scraper.py      │◄────│  (campaigns,     │
│  (Apify + APIs)  │     │   sources, CVs)  │
└────────┬─────────┘     └──────────────────┘
         ▼
┌──────────────────┐
│  Module 2        │
│  cleaner.py      │
│  (dedup, filter) │
└────────┬─────────┘
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Module 3        │     │  data/           │
│  matcher.py      │◄────│  cv_*.docx       │
│  (CV scoring)    │     │  (your CVs)      │
└────────┬─────────┘     └──────────────────┘
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Module 4        │     │  Claude API      │
│  tailor.py       │◄────│  (generates      │
│  (AI tailoring)  │     │   cover letters) │
└────────┬─────────┘     └──────────────────┘
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Module 5        │────►│  data/           │
│  tracker.py      │     │  job_tracker.xlsx│
│  (Excel output)  │     └──────────────────┘
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Module 6        │────► Email to your inbox
│  alerter.py      │
│  (daily digest)  │
└──────────────────┘
```

## Project structure

```
job_pipeline/
├── run_pipeline.py          # Master script — runs everything
├── config.py                # All configuration — campaigns, sources, CVs, thresholds
├── .env                     # API keys and secrets (not committed to git)
├── .gitignore
├── requirements.txt
│
├── modules/
│   ├── __init__.py
│   ├── scraper.py           # Module 1 — job board scraping
│   ├── cleaner.py           # Module 2 — deduplication and filtering
│   ├── matcher.py           # Module 3 — CV semantic scoring
│   ├── tailor.py            # Module 4 — AI cover letter + ATS answers
│   ├── tracker.py           # Module 5 — Excel tracking
│   └── alerter.py           # Module 6 — email digest
│
├── data/
│   ├── cv_powerbi_bi.docx   # Your Power BI / BI Developer CV
│   ├── cv_data_analyst.docx # Your Data Analyst / Business Analyst CV
│   ├── cv_engineering.docx  # Your Data Engineering CV
│   └── job_tracker.xlsx     # Auto-generated on first run
│
└── output/
    └── CompanyName_JobTitle/
        ├── cover_letter.docx
        └── ats_answers.docx
```

## Setup

### Prerequisites

- Python 3.10 or higher
- An Apify account (free tier works for light usage, $49/month starter recommended for daily runs)
- An Anthropic API key (for Claude-powered cover letter generation)
- A Gmail account with an App Password (for email alerts)

### Installation

Clone the repository and set up the environment:

```bash
git clone https://github.com/yourusername/job-pipeline.git
cd job-pipeline
python -m venv venv
```

Activate the virtual environment:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install apify-client python-dotenv pandas requests sentence-transformers scikit-learn python-docx anthropic openpyxl
```

### Environment variables

Create a `.env` file in the project root:

```env
APIFY_API_TOKEN=your_apify_token
ANTHROPIC_API_KEY=your_claude_api_key
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
```

**Getting each key:**

- **Apify**: Sign up at apify.com, go to Settings → Integrations → API Token
- **Anthropic**: Sign up at console.anthropic.com, go to API Keys → Create Key
- **Gmail App Password**: Go to myaccount.google.com → Security → 2-Step Verification (enable it), then go to myaccount.google.com/apppasswords and create a password for "Mail"

### Place your CVs

Copy your CV files into the `data/` folder:

```
data/cv_powerbi_bi.docx    — Power BI / BI Developer CV
data/cv_data_analyst.docx  — Data Analyst / Business Analyst CV
data/cv_engineering.docx   — Data Engineering CV
```

The filenames must match what's defined in `config.py` under the `CVS` dictionary. You can add more CVs by adding entries there.

## Usage

### Run the full pipeline

```bash
python run_pipeline.py
```

This runs all 6 modules: scrape → clean → score → tailor → track → alert.

### Run a specific campaign only

```bash
python run_pipeline.py --campaign analyst_nigeria_africa
```

### Skip cover letter generation (faster)

```bash
python run_pipeline.py --skip-tailor
```

### Skip email alert

```bash
python run_pipeline.py --skip-alert
```

### Skip both (fastest — just find, score, and track)

```bash
python run_pipeline.py --skip-tailor --skip-alert
```

### Run individual modules for testing

Each module can be run independently:

```bash
python -m modules.scraper    # Test scraping only
python -m modules.cleaner    # Test scraping + cleaning
python -m modules.matcher    # Test scraping + cleaning + scoring
python -m modules.tailor     # Test full pipeline through tailoring
python -m modules.tracker    # Test full pipeline through Excel tracking
python -m modules.alerter    # Test email alert with dummy data
```

## Configuration

All configuration lives in `config.py`. You never need to edit Python module files to change what the pipeline searches for.

### Campaigns

Campaigns define what roles to search for, where to search, which CV to use, and which job boards to scrape. Each campaign runs independently.

```python
"analyst_nigeria_africa": {
    "enabled":         True,               # Toggle on/off
    "description":     "Data/Business/BI Analyst — Nigeria & Africa",
    "cv":              CVS["data_analyst"], # Which CV to score and tailor against
    "roles":           ["Data Analyst", "Business Analyst", "BI Analyst"],
    "keywords":        ["Data Analyst", "Business Analyst"],
    "remotive_keywords": ["data analyst", "business analyst"],
    "locations":       ["Nigeria", "Lagos", "Abuja", "Africa"],
    "country_codes":   ["NG"],             # Indeed country filter
    "remote_only":     False,              # True = remote only, False = any work model
    "sources":         ["linkedin", "indeed", "jobberman", "myjobmag", "remotive"],
    "max_age_hours":   DATE_PRESETS["1_week"],  # How far back to look
    "match_threshold": 0.45,               # Minimum CV match score (0.0 to 1.0)
}
```

### Adding a new campaign

Add a new block to the `CAMPAIGNS` dictionary in `config.py`. No code changes needed anywhere else.

### Adding a new CV

1. Place the `.docx` file in `data/`
2. Add an entry to the `CVS` dictionary in `config.py`
3. Reference it in whichever campaigns should use it

### Adding a new job board

If the board has an Apify Actor:

1. Add an entry to `SOURCES` with the Actor name
2. Add the source key to whichever campaign's `sources` list

If the board has a free API:

1. Add a scraper function in `modules/scraper.py`
2. Add it to `SOURCES` and campaign source lists

### Date filter presets

Control how far back to look for jobs:

```python
DATE_PRESETS = {
    "24h":     24,
    "48h":     48,
    "72h":     72,
    "1_week":  168,
    "2_weeks": 336,
    "1_month": 720,
    "off":     0,      # No date filtering
}
```

Use them in campaigns like: `"max_age_hours": DATE_PRESETS["1_week"]`

### Match threshold

The `match_threshold` controls how closely a job must match your CV to be included. The scoring uses cosine similarity between your CV and the job description, producing a score from 0.0 (completely unrelated) to 1.0 (perfect match).

Guidelines:

- **0.40 - 0.50**: Broad matching, more results, some noise. Good for niche markets with fewer listings.
- **0.50 - 0.60**: Balanced. Recommended starting point for most campaigns.
- **0.60+**: Strict matching, fewer but highly relevant results.

### Sources available

| Source | Type | Best for |
|--------|------|----------|
| LinkedIn | Apify | Professional roles globally |
| Indeed | Apify | High volume, all regions |
| Jobberman | Apify | Nigeria's largest job board |
| MyJobMag | Apify | Pan-African roles |
| Remotive | Free API | Remote-only tech roles |
| RemoteOK | Free API | Remote tech and data roles |
| We Work Remotely | Apify | Curated remote roles |
| Wellfound | Apify | Startup and scale-up roles |
| Glassdoor | Apify | Roles with salary data |

Apify sources require credits. Free API sources have no cost.

## Excel tracker

The pipeline creates `data/job_tracker.xlsx` as a proper Excel Table on the first run. Subsequent runs append new rows without duplicating jobs already tracked.

### Auto-filled columns

These are populated by the pipeline on every run:

- Date Found, Campaign, Job Title, Company, Source, Location, Match Score, Job URL, Cover Letter path, ATS Answers path, Status (set to "New")

### Manual columns

You update these yourself after applying:

- Status (change from "New" to "Applied", "Interview", "Offer", "Rejected", or "Withdrawn")
- Date Applied
- Interview Date
- Notes

### Filtering and sorting

The tracker is a proper Excel Table. You can filter by campaign, source, score range, or status directly in Excel using the dropdown arrows on each column header.

## Filtering logic

The cleaner module applies several filters in sequence:

1. **HTML stripping** — removes HTML tags from job descriptions
2. **Empty field removal** — drops jobs missing a title or company name
3. **Date filter** — removes jobs older than the campaign's `max_age_hours`
4. **Remote filter** — for `remote_only` campaigns, drops anything without a clear remote signal in the title or location
5. **Language filter** — drops jobs requiring Spanish, French, Portuguese, Arabic, or German fluency
6. **Geographic filter** — for Nigeria/Africa campaigns, drops jobs explicitly restricted to US, UK, EU, or other non-African locations
7. **Deduplication** — first by exact URL, then by company + normalised title
8. **Already-seen filter** — skips any job URL already in the Excel tracker

## AI tailoring

Module 4 uses the Claude API to generate a cover letter and pre-filled ATS answers for each matched job. The prompt is engineered to avoid AI-detection patterns:

- Banned words list (spearheaded, leveraged, orchestrated, etc.)
- Banned phrases list (generic openers, press-release language)
- Banned structural patterns (formulaic "Not only X but Y" constructions)
- Em dashes explicitly forbidden with post-processing fallback
- Contractions required throughout
- Candidate's original voice and specific experience preserved

Generated files are saved in `output/CompanyName_JobTitle/` as Word documents.

## Scheduling (optional)

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → name it "Job Pipeline"
3. Set trigger to Daily at your preferred time (e.g., 7:00 AM)
4. Action → Start a Program
5. Program: `C:\Users\yourname\Documents\job_pipeline\venv\Scripts\python.exe`
6. Arguments: `run_pipeline.py`
7. Start in: `C:\Users\yourname\Documents\job_pipeline`

### Linux / macOS (cron)

```bash
crontab -e
```

Add:

```
0 7 * * * cd /path/to/job_pipeline && /path/to/venv/bin/python run_pipeline.py
```

## Cost

- **Apify free tier**: $5/month of compute credits. Enough for light testing. Daily runs across multiple campaigns will likely need the $49/month Starter plan.
- **Claude API**: approximately $0.01-0.03 per job tailored (cover letter + ATS answers). A daily run matching 10 jobs costs roughly $0.10-0.30/day.
- **Remotive, RemoteOK**: completely free, no API key needed.
- **Gmail SMTP**: free.

## Troubleshooting

**"Monthly usage hard limit exceeded"** — Apify free tier credits are exhausted. Check your billing reset date at apify.com → Settings → Billing, or upgrade to Starter.

**"ModuleNotFoundError"** — virtual environment is not activated. Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux).

**"cannot import name from 'config'"** — a system-level `config` package is shadowing your `config.py`. The `sys.path.insert` line at the top of each module handles this automatically, but if issues persist, run modules with `python -m modules.scraper` instead of `python modules/scraper.py`.

**"CV not found"** — your CV file isn't in `data/` or the filename doesn't match what's defined in `config.py` under `CVS`.

**"GMAIL_APP_PASSWORD not found"** — add your Gmail App Password to `.env`. You need 2-Step Verification enabled on your Google account first, then create an App Password at myaccount.google.com/apppasswords.

**Pandas SettingWithCopyWarning** — harmless warning, does not affect output. The `df.copy()` call in `remove_duplicates` suppresses it.

**Zero jobs after cleaning** — the filters are working correctly but all scraped jobs were noise. This typically happens when only free API sources are active (Remotive, RemoteOK) and Apify is down. Once Apify resets, LinkedIn, Indeed, Jobberman, and MyJobMag will return relevant local listings.

## Built with

- Python 3.12
- Apify (LinkedIn, Indeed, Jobberman, MyJobMag scrapers)
- sentence-transformers (all-MiniLM-L6-v2 model for CV matching)
- Anthropic Claude API (cover letter and ATS answer generation)
- openpyxl (Excel Table creation and management)
- pandas (data processing)

## License

This project is for personal use. Feel free to fork and adapt for your own job search.
