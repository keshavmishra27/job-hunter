# Agent.md — Startup Contact Discovery Agent

## Objective
Build an agent that finds **publicly available business contact emails** for small startups and returns the best contact point for internship outreach.

The agent should:
1. Discover startup websites and public company pages.
2. Extract public contact emails from contact, careers, team, and about pages.
3. Infer likely company email patterns only when necessary.
4. Rank contacts by relevance for internship outreach.
5. Return structured results with confidence and source evidence.

## Scope
This agent is only for **public business contact discovery**.

### Allowed sources
- Company website pages: `/contact`, `/careers`, `/about`, `/team`, `/jobs`
- Public startup directories
- Public company profiles
- Public press pages
- Public GitHub organization pages with listed contact info
- Public contact forms or listed business emails

### Not in scope
- Private or personal emails
- LinkedIn scraping that bypasses access restrictions
- Hidden data extraction
- Account-based login scraping
- Sending emails automatically in this step

## Output format
For each startup, return:

```json
{
  "company_name": "string",
  "website": "string",
  "startup_size": "string",
  "contacts": [
    {
      "name": "string",
      "role": "string",
      "email": "string",
      "source_url": "string",
      "source_type": "contact_page|careers_page|team_page|about_page|public_directory|pattern_inference",
      "confidence": 0.0,
      "notes": "string"
    }
  ],
  "best_contact": {
    "name": "string",
    "role": "string",
    "email": "string",
    "confidence": 0.0
  }
}
```

## Contact priority rules
Rank contacts in this order:
1. Founder / Co-founder
2. CTO / Head of Engineering
3. Engineering Lead / Hiring Manager
4. HR / Talent
5. Careers / Jobs inbox
6. Generic business inbox

For small startups, founder and CTO often matter more than HR.

## Discovery pipeline

### Step 1: Startup seed input
Input can include:
- startup name
- website
- LinkedIn company URL
- YC company page
- Wellfound company page
- Product Hunt page

### Step 2: Website crawl
Fetch and inspect:
- homepage
- contact page
- careers page
- about page
- team page
- jobs page

Use polite crawling:
- respect robots.txt
- low request rate
- timeout and retry limits
- avoid aggressive crawling

### Step 3: Email extraction
Extract only public emails from:
- visible page text
- mailto links
- footer contact blocks
- structured data / schema markup

Regex example:
```python
r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
```

### Step 4: Role detection
Detect names and roles from nearby text:
- Founder
- Co-founder
- CTO
- Engineer
- Hiring
- Talent
- HR

### Step 5: Pattern inference
If no email is listed publicly:
- infer likely company email patterns from publicly visible names
- only use if there is strong evidence
- mark as `pattern_inference`
- lower confidence than direct extraction

Common patterns:
- firstname@domain.com
- first.last@domain.com
- firstinitiallastname@domain.com

### Step 6: Scoring
Assign a score to each contact:

```text
score =
  source_quality +
  role_priority +
  relevance_to_startup_size +
  confidence
```

Recommended scoring:
- Founder / CTO contact: +40
- HR / Talent: +25
- careers@ / jobs@ inbox: +20
- Direct public email on contact page: +30
- Pattern inference: +10 to +15
- High confidence source: +20
- Low confidence source: +5

### Step 7: Deduplication
Remove duplicates across:
- same email
- same person with multiple sources
- repeated company pages

## Safety and compliance rules
- Use only public business contact information.
- Do not scrape private personal data.
- Do not evade login walls.
- Do not generate or store emails from hidden sources.
- Add an opt-out flag for outreach later.
- Rate-limit extraction and emailing workflows.
- Keep a source trail for every email.

## Suggested backend modules

### `startup_discovery.py`
Find startup websites and public pages.

### `contact_extractor.py`
Extract emails, names, and roles from HTML/text.

### `email_pattern_inferer.py`
Infer likely business email patterns when public email is missing.

### `contact_ranker.py`
Rank contacts by role, source quality, and confidence.

### `startup_scanner.py`
Coordinate crawling, parsing, scoring, and output.

### `schemas.py`
Define Pydantic models for structured output.

## Suggested API endpoints

### `POST /discover/startup-contacts`
Input:
```json
{
  "company_name": "string",
  "website": "string",
  "source_hint": "string"
}
```

### `POST /discover/batch`
Input:
```json
{
  "startups": [
    {
      "company_name": "string",
      "website": "string"
    }
  ]
}
```

### `GET /discover/health`
Health check for crawler and extractor.

## Database tables

### `startup_profiles`
- id
- company_name
- website
- size_estimate
- source_hint
- created_at

### `startup_contacts`
- id
- startup_id
- name
- role
- email
- source_url
- source_type
- confidence
- is_best_contact

### `scan_logs`
- id
- startup_id
- status
- error
- scanned_at

## Recommended implementation order

1. Build HTML fetcher for public pages.
2. Build email regex extractor.
3. Build role/name extractor from surrounding text.
4. Add ranking and confidence scoring.
5. Add fallback pattern inference.
6. Add deduplication.
7. Add JSON API response.
8. Add batch processing.
9. Add logging and retry handling.
10. Add tests with sample startup pages.

## Acceptance criteria
- Finds public business emails from startup websites.
- Correctly identifies at least one best contact when available.
- Produces structured JSON output.
- Attaches source evidence for each email.
- Handles missing emails with pattern inference and lower confidence.
- Does not rely on private or restricted sources.

## Notes for the IDE agent
- Keep the code modular.
- Prefer deterministic extraction before LLM inference.
- Use LLMs only for ambiguous name/role parsing.
- Return confidence scores and source URLs for every result.
- Treat this as a discovery and ranking system, not a mass-email system.
