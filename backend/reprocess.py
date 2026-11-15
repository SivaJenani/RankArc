"""
Reprocess paper 11 (the SSC CGL PDF) with the fixed multi-shift parser.
Run from E:\Rankly\backend directory.
"""
import asyncio
import sys
sys.path.insert(0, r'E:\Rankly\backend')

async def main():
    from app.services.llm_extractor import process_paper
    from app.config import get_settings

    settings = get_settings()
    # Paper 11 file path from DB
    import sqlite3
    conn = sqlite3.connect(r'E:\Rankly\backend\rankly.db')
    row = conn.execute('SELECT id, file_path FROM papers WHERE id=11').fetchone()
    conn.close()

    print(f"Reprocessing paper {row[0]} at {row[1]}", flush=True)
    
    # First reset the paper status so process_paper can run
    import sqlite3
    conn = sqlite3.connect(r'E:\Rankly\backend\rankly.db')
    conn.execute("UPDATE papers SET status='uploading' WHERE id=11")
    conn.execute("DELETE FROM questions WHERE paper_id=11")
    conn.commit()
    conn.close()
    print("Reset status and cleared old questions", flush=True)
    
    await process_paper(11, row[1], settings)
    print("Done!", flush=True)

asyncio.run(main())
