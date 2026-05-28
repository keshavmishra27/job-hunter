import sqlite3
conn=sqlite3.connect('data/job_hunter.db')
c=conn.cursor()
try:
    q = """
    select a.id, a.user_id, a.job_id, a.status, a.applied_at, j.id, j.title
    from applications a
    join job_posts j on a.job_id = j.id
    where a.user_id = ?
    order by a.applied_at desc
    """
    rows=list(c.execute(q, ('demo-user-1',)).fetchall())
    print('JOIN ROWS', len(rows))
    for r in rows[:20]:
        print(r)
except Exception as e:
    print('ERR',e)
finally:
    conn.close()
