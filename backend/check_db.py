import sqlite3, json

conn = sqlite3.connect(r'E:\Rankly\backend\rankly.db')

# Latest paper details
row = conn.execute('SELECT id, title, status, meta FROM papers WHERE id=11').fetchone()
print("Paper 11 status:", row[2])
meta = json.loads(row[3]) if row[3] else {}
print("exam_title:", meta.get("exam_title"))
print("duration_minutes:", meta.get("duration_minutes"))
sets = meta.get("paper_sets", [])
print(f"paper_sets ({len(sets)}):")
for ps in sets:
    print(" ", ps)

qcount = conn.execute(
    'SELECT paper_set, COUNT(*) FROM questions WHERE paper_id=11 GROUP BY paper_set'
).fetchall()
print("\nQuestion counts per paper_set:")
total = 0
for qs in qcount:
    print(f"  {qs[0]}: {qs[1]}")
    total += qs[1]
print(f"  TOTAL: {total}")

# Check for a stuck paper (status=processing)
stuck = conn.execute("SELECT id, title, status, created_at FROM papers WHERE status='processing'").fetchall()
print("\nStuck papers (processing):")
for s in stuck:
    print(" ", s)

conn.close()
