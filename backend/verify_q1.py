import sqlite3

conn = sqlite3.connect(r'E:\Rankly\backend\rankly.db')
cursor = conn.cursor()
rows = cursor.execute("""
    SELECT question_number, paper_set, question_text, image_url 
    FROM questions 
    WHERE paper_id=11 AND question_number IN (1, 2) AND paper_set LIKE '%9 OCT%'
""").fetchall()

for r in rows:
    print(f"Set: {r[1]} | Q{r[0]}")
    print(f"  Stem: {r[2]}")
    print(f"  Image: {r[3]}")

conn.close()
