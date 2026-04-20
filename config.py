import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
#  API Keys
# ─────────────────────────────────────────
APIFY_API_TOKEN  = os.getenv("APIFY_API_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ─────────────────────────────────────────
#  CVs
# ─────────────────────────────────────────
CVS = {
    "powerbi_bi":   "data/cv_powerbi_bi.docx",
    "data_analyst": "data/cv_data_analyst.docx",
    "engineering":  "data/cv_engineering.docx",
}

# ─────────────────────────────────────────
#  Date filter presets (use in campaigns)
#  Set max_age_hours to any of these or 0 to disable
# ─────────────────────────────────────────
DATE_PRESETS = {
    "24h":     24,
    "48h":     48,
    "72h":     72,
    "1_week":  168,
    "2_weeks": 336,
    "1_month": 720,
    "off":     0,
}

# ─────────────────────────────────────────
#  Sources
# ─────────────────────────────────────────
SOURCES = {
    # Core global boards
    "linkedin": {
        "enabled": True,
        "type":    "apify",
        "actor":   "curious_coder/linkedin-jobs-scraper",
    },
    "indeed": {
        "enabled": True,
        "type":    "apify",
        "actor":   "misceres/indeed-scraper",
    },
    "remotive": {
        "enabled": True,
        "type":    "api",
    },
    "remoteok": {
        "enabled": True,
        "type":    "api",
    },
    "weworkremotely": {
        "enabled": True,
        "type":    "apify",
        "actor":   "tugkan/we-work-remotely-scraper",
    },

    # Nigeria / Africa specific
    "jobberman": {
        "enabled": True,
        "type":    "apify",
        "actor":   "curious_coder/jobberman-scraper",
    },
    "myjobmag": {
        "enabled": True,
        "type":    "apify",
        "actor":   "tugkan/myjobmag-scraper",
    },

    # Off for now
    "wellfound": {
        "enabled": False,
        "type":    "apify",
        "actor":   "bebity/wellfound-jobs-scraper",
    },
    "glassdoor": {
        "enabled": False,
        "type":    "apify",
        "actor":   "bebity/glassdoor-jobs-scraper",
    },
    "dice": {
        "enabled": False,
        "type":    "apify",
        "actor":   "bebity/dice-jobs-scraper",
    },
    "themuse": {
        "enabled": False,
        "type":    "api",
    },
    "arbeitnow": {
        "enabled": False,
        "type":    "api",
    },
}

# ─────────────────────────────────────────
#  Remote / location filter keywords
# ─────────────────────────────────────────
REMOTE_KEYWORDS = [
    "remote", "work from home", "fully remote",
    "wfh", "home based", "home-based", "anywhere",
    "hybrid", "hybrid remote",
]

EXCLUDE_KEYWORDS = [
    "on-site only", "onsite only", "no remote",
    "office based only", "must be in office",
    "relocation required", "on site only",
]

# ─────────────────────────────────────────
#  Campaigns — only Nigeria/Africa active
# ─────────────────────────────────────────
CAMPAIGNS = {

    # ── Active: Analyst roles in Nigeria/Africa ──────────────────────
    "analyst_nigeria_africa": {
        "enabled":     True,
        "description": "Data/Business/BI Analyst — Nigeria & Africa",
        "cv":          CVS["data_analyst"],

        "roles": [
            "Data Analyst",
            "Business Analyst",
            "Business Intelligence Analyst",
            "BI Analyst",
            "Reporting Analyst",
        ],

        "keywords": [
            "Data Analyst",
            "Business Analyst",
            "BI Analyst",
            "Business Intelligence Analyst",
            "Reporting Analyst",
        ],

        "remotive_keywords": ["data analyst", "business analyst", "business intelligence"],

        "locations":      ["Nigeria", "Lagos", "Abuja", "Africa"],
        "country_codes":  ["NG"],
        "remote_only":    False,
        "sources": ["linkedin", "indeed", "jobberman", "myjobmag", "remotive"],
        "max_age_hours":  DATE_PRESETS["off"],     # change to DATE_PRESETS["1_week"] etc for production
        "match_threshold": 0.45,
    },

    # ── Active: Power BI / BI Developer in Nigeria/Africa ────────────
    "powerbi_nigeria_africa": {
        "enabled":     True,
        "description": "Power BI / BI Developer — Nigeria & Africa",
        "cv":          CVS["powerbi_bi"],

        "roles": [
            "Power BI Developer",
            "BI Developer",
            "Business Intelligence Developer",
            "Power BI Analyst",
            "Reporting Developer",
        ],

        "keywords": [
            "Power BI Developer",
            "BI Developer",
            "Business Intelligence Developer",
            "Power BI Analyst",
        ],

        "remotive_keywords": ["power bi", "business intelligence developer", "bi developer"],

        "locations":      ["Nigeria", "Lagos", "Abuja", "Africa"],
        "country_codes":  ["NG"],
        "remote_only":    False,
        "sources": ["linkedin", "indeed", "jobberman", "myjobmag", "remotive"],
        "max_age_hours":  DATE_PRESETS["off"],
        "match_threshold": 0.45,
    },

    # ── Disabled: expand later ───────────────────────────────────────
    "analyst_global_remote": {
        "enabled":     False,
        "description": "Data/Business/BI Analyst — Global Remote Only",
        "cv":          CVS["data_analyst"],
        "roles":       ["Data Analyst", "Business Analyst", "BI Analyst"],
        "keywords":    ["Data Analyst Remote", "Business Analyst Remote", "BI Analyst Remote"],
        "remotive_keywords": ["data analyst", "business analyst"],
        "locations":      ["Remote", "Worldwide"],
        "country_codes":  ["US", "GB", "CA", "AU"],
        "remote_only":    True,
        "sources":        ["linkedin", "indeed", "remotive", "remoteok", "weworkremotely"],
        "max_age_hours":  DATE_PRESETS["48h"],
        "match_threshold": 0.50,
    },

    "powerbi_global_remote": {
        "enabled":     False,
        "description": "Power BI / BI Developer — Global Remote Only",
        "cv":          CVS["powerbi_bi"],
        "roles":       ["Power BI Developer", "BI Developer", "Business Intelligence Developer"],
        "keywords":    ["Power BI Developer Remote", "BI Developer Remote"],
        "remotive_keywords": ["power bi", "bi developer"],
        "locations":      ["Remote", "Worldwide"],
        "country_codes":  ["US", "GB", "CA", "AU"],
        "remote_only":    True,
        "sources":        ["linkedin", "indeed", "remotive", "remoteok", "weworkremotely"],
        "max_age_hours":  DATE_PRESETS["48h"],
        "match_threshold": 0.50,
    },

    "engineering_global_remote": {
        "enabled":     False,
        "description": "Data Engineer — Global Remote Only",
        "cv":          CVS["engineering"],
        "roles":       ["Data Engineer", "Analytics Engineer"],
        "keywords":    ["Data Engineer Remote", "Analytics Engineer Remote"],
        "remotive_keywords": ["data engineer"],
        "locations":      ["Remote", "Worldwide"],
        "country_codes":  ["US", "GB", "CA"],
        "remote_only":    True,
        "sources":        ["linkedin", "indeed", "remotive", "weworkremotely"],
        "max_age_hours":  DATE_PRESETS["48h"],
        "match_threshold": 0.55,
    },
}