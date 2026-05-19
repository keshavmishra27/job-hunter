"""Diagnostic: check actual data and test project overlap scoring."""
import sqlite3
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "job_hunter.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# 1. User profile
print("=" * 60)
print("USER PROFILE")
print("=" * 60)
rows = conn.execute("SELECT user_id, skills, projects, preferred_roles, location_rule FROM user_profiles LIMIT 5").fetchall()
for row in rows:
    skills = json.loads(row['skills']) if row['skills'] else []
    projects = json.loads(row['projects']) if row['projects'] else []
    roles = json.loads(row['preferred_roles']) if row['preferred_roles'] else []
    loc = json.loads(row['location_rule']) if row['location_rule'] else {}
    print(f"\n  user_id: {row['user_id']}")
    print(f"  skills ({len(skills)}): {skills}")
    print(f"  projects ({len(projects)}): {projects}")
    print(f"  preferred_roles: {roles}")
    print(f"  location_rule: {loc}")

# 2. GitHub repos
print("\n" + "=" * 60)
print("GITHUB REPOS")
print("=" * 60)
repos = conn.execute("""
    SELECT id, user_id, name, description, language, languages_all, topics 
    FROM repo_entries WHERE is_archived = 0 LIMIT 15
""").fetchall()
print(f"\n  Total non-archived repos: {len(repos)}")
for repo in repos[:10]:
    langs = json.loads(repo['languages_all']) if repo['languages_all'] else {}
    topics = json.loads(repo['topics']) if repo['topics'] else []
    print(f"\n  [{repo['name']}]")
    print(f"    language: {repo['language']}")
    print(f"    languages_all: {list(langs.keys()) if langs else 'None'}")
    print(f"    topics: {topics}")
    print(f"    description: {(repo['description'] or 'None')[:80]}")

# 3. Current stored job match scores
print("\n" + "=" * 60)
print("SAMPLE STORED JOB MATCHES (first 10 by score)")
print("=" * 60)
matches = conn.execute("""
    SELECT m.job_id, m.score, m.score_breakdown, m.matched_skills, m.matched_projects,
           j.title, j.company, j.description
    FROM job_matches m
    JOIN job_posts j ON m.job_id = j.id
    ORDER BY m.score DESC
    LIMIT 10
""").fetchall()
for m in matches:
    bd = json.loads(m['score_breakdown']) if m['score_breakdown'] else {}
    mp = json.loads(m['matched_projects']) if m['matched_projects'] else []
    desc_len = len(m['description'] or '')
    print(f"\n  [{m['title']}] @ {m['company']}")
    print(f"    score={m['score']}, project_overlap={bd.get('project_overlap', '?')}")
    print(f"    matched_projects: {mp}")
    print(f"    desc length: {desc_len} chars")

# 4. Test new scoring logic
print("\n" + "=" * 60)
print("LIVE TEST: new _project_overlap logic")
print("=" * 60)
from backend.modules.ranker import _extract_tech_from_text, _project_overlap

user_row = conn.execute("SELECT skills, projects FROM user_profiles LIMIT 1").fetchone()
profile = {
    "skills": json.loads(user_row['skills']) if user_row['skills'] else [],
    "projects": json.loads(user_row['projects']) if user_row['projects'] else [],
}

github_repos_data = []
for repo in repos:
    langs = json.loads(repo['languages_all']) if repo['languages_all'] else {}
    topics = json.loads(repo['topics']) if repo['topics'] else []
    github_repos_data.append({
        "id": repo['id'], "name": repo['name'],
        "description": repo['description'], "language": repo['language'],
        "languages_all": langs, "topics": topics, "analysis_signals": {},
    })

print(f"\n  Profile projects ({len(profile['projects'])}):")
for proj in profile['projects']:
    techs = _extract_tech_from_text(proj)
    print(f"    '{proj[:60]}' -> tech: {techs if techs else 'NONE'}")

print(f"\n  GitHub repos ({len(github_repos_data)}):")
for r in github_repos_data[:5]:
    repo_text = f"{r['description'] or ''} {' '.join(r['topics'])} {r['language'] or ''} {' '.join(k.lower() for k in r['languages_all'].keys())}"
    repo_techs = _extract_tech_from_text(repo_text)
    print(f"    [{r['name']}] -> tech: {repo_techs if repo_techs else 'NONE'}")

# Test 5 random jobs
print("\n  Testing against 5 jobs from DB:")
sample_jobs = conn.execute("""
    SELECT j.title, j.company, j.description FROM job_posts j
    JOIN job_matches m ON m.job_id = j.id
    ORDER BY m.score DESC LIMIT 5
""").fetchall()
for j in sample_jobs:
    job = {"title": j['title'], "company": j['company'], "description": j['description']}
    full_text = f"{job['title']} {job['description'] or ''} {job['company']}"
    job_techs = _extract_tech_from_text(full_text)
    score, matched = _project_overlap(job, profile, github_repos_data)
    print(f"\n    [{job['title']}] @ {job['company']}")
    print(f"      job techs: {job_techs}")
    print(f"      overlap score: {score:.2f}, matched: {matched}")

conn.close()
print("\nDone.")
