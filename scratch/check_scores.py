"""Quick check: verify updated scores in DB after re-fetch."""
import sqlite3, json
conn = sqlite3.connect('data/job_hunter.db')
conn.row_factory = sqlite3.Row

matches = conn.execute("""
    SELECT m.score, m.score_breakdown, m.matched_projects,
           j.title, j.company
    FROM job_matches m
    JOIN job_posts j ON m.job_id = j.id
    ORDER BY m.score DESC
    LIMIT 15
""").fetchall()

print(f"{'Title':<45} {'Score':>6} {'ProjOv':>7} {'Matched Projects'}")
print("-" * 110)
for m in matches:
    bd = json.loads(m['score_breakdown']) if m['score_breakdown'] else {}
    mp = json.loads(m['matched_projects']) if m['matched_projects'] else []
    po = bd.get('project_overlap', 0)
    print(f"{(m['title'] or 'Unknown')[:44]:<45} {m['score']:>6.3f} {po:>7.1%} {mp}")

conn.close()
