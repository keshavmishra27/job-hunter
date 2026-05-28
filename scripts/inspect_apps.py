import sqlite3
conn=sqlite3.connect('data/job_hunter.db')
c=conn.cursor()
try:
    rows=list(c.execute("select id, user_id, job_id, status, applied_at from applications order by applied_at desc limit 50"))
    for r in rows:
        print(r)
    print('\nTOTAL', c.execute('select count(*) from applications').fetchone())
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
