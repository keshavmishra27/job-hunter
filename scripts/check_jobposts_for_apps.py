import sqlite3
conn=sqlite3.connect('data/job_hunter.db')
c=conn.cursor()
try:
    app_rows=list(c.execute("select id, user_id, job_id, status, applied_at from applications order by applied_at desc"))
    print('Applications:', len(app_rows))
    missing = []
    for app in app_rows:
        aid, uid, jid, status, at = app
        job = c.execute('select id, title from job_posts where id=?', (jid,)).fetchone()
        if not job:
            missing.append((aid, jid))
    print('Missing job_posts for', len(missing), 'applications')
    for m in missing[:20]:
        print(m)
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
