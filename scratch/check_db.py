import sqlite3

conn = sqlite3.connect("data/job_hunter.db")
c = conn.cursor()

# Check applications
c.execute("SELECT job_id, status, job_fingerprint FROM applications WHERE user_id='demo-user-1'")
applied = c.fetchall()
print(f"Applications ({len(applied)}):")
for a in applied:
    print(f"  job_id={a[0]}, status={a[1]}, fp={a[2]}")

# Check what the 13 job_matches look like
c.execute("""
    SELECT jm.job_id, jp.title, jp.company, jp.source, jm.score
    FROM job_matches jm
    JOIN job_posts jp ON jm.job_id = jp.id
    WHERE jm.user_id='demo-user-1'
    ORDER BY jm.score DESC
""")
matches = c.fetchall()
print(f"\nJob matches ({len(matches)}):")
for m in matches:
    print(f"  {m[1]} @ {m[2]} (src={m[3]}, score={m[4]})")

# Check how many Internshala titles are 'Unknown'
c.execute("SELECT COUNT(*) FROM job_posts WHERE title='Unknown' AND source='Internshala'")
print(f"\nInternshala 'Unknown' title count: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM job_posts WHERE title!='Unknown' AND source='Internshala'")
print(f"Internshala valid title count: {c.fetchone()[0]}")

# Check Indeed titles
c.execute("SELECT title, company FROM job_posts WHERE source='Indeed' LIMIT 10")
print(f"\nIndeed titles (sample):")
for r in c.fetchall():
    print(f"  {r[0]} @ {r[1]}")

conn.close()
