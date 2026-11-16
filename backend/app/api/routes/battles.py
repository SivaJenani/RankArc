"""Isolated single-process, two-player preview. No changes to individual attempts.
Room snapshots and answers live in BATTLE_DB; process restart cancels open rooms.
Run exactly one application worker. This is a casual practice feature, not anti-cheat.
"""
import base64
import copy
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import get_current_user
from app.db import get_db
from app.models.paper import Paper
from app.models.question import Question, Option

router = APIRouter(tags=['battles'])
GENERATION = secrets.token_hex(16)
SYNTHETIC = json.loads((Path(__file__).parents[2] / 'data' / 'battle_synthetic.json').read_text())

def now():
    return time.time()

@contextmanager
def transaction():
    path = Path(os.getenv('BATTLE_DB', str(Path(get_settings().upload_dir) / 'battle-state.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, body TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS queue (uid INTEGER PRIMARY KEY, code TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS assets (code TEXT NOT NULL, number INTEGER NOT NULL, data BLOB NOT NULL, PRIMARY KEY(code,number))')
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def save(conn, room):
    conn.execute('INSERT OR REPLACE INTO rooms VALUES (?,?)', (room['code'], json.dumps(room)))

def settle(room):
    if room['status'] in ('waiting', 'active') and room['generation'] != GENERATION:
        room.update(status='cancelled', reason='Server restarted. Match cancelled; no winner.')
    elif room['status'] == 'waiting' and now() >= room['expires_at']:
        room.update(status='cancelled', reason='Room expired; no winner.')
    elif room['status'] == 'active' and (now() >= room['deadline'] or all(p['submitted'] for p in room['players'].values())):
        room['status'] = 'finished'
        for p in room['players'].values(): p['submitted'] = True
        room['finished_at'] = now()
    return room

def load(conn, code):
    row = conn.execute('SELECT body FROM rooms WHERE code=?', (code.upper(),)).fetchone()
    if not row:
        raise HTTPException(404, 'Room unavailable. It may have expired or temporary storage was lost. No winner recorded.')
    room = settle(json.loads(row[0])); save(conn, room)
    return room

def member(room, user):
    if str(user.id) not in room['players']:
        raise HTTPException(404, 'Room not found')
    return room['players'][str(user.id)]

def player(number):
    return {'alias':f'Player {number}', 'ready':False, 'submitted':False, 'answers':{}}

def new_room(conn, uid, title, questions, duration, mode):
    # One waiting/active room per player, and no unbounded room creation.
    for raw, in conn.execute('SELECT body FROM rooms').fetchall():
        existing = settle(json.loads(raw)); save(conn, existing)
        if str(uid) in existing['players'] and existing['status'] in ('waiting','active'):
            raise HTTPException(409, 'Leave or finish your current room first.')
    if conn.execute('SELECT count(*) FROM rooms').fetchone()[0] >= 200:
        raise HTTPException(503, 'Local preview room limit reached. No new room created.')
    pages = conn.execute('PRAGMA page_count').fetchone()[0]
    size = conn.execute('PRAGMA page_size').fetchone()[0]
    if pages * size >= 64_000_000:
        raise HTTPException(503, 'Local preview storage limit reached. No new room created.')
    code = secrets.token_hex(6).upper()
    for q in questions:
        if isinstance(q.get('image'), str):
            conn.execute('INSERT INTO assets VALUES (?,?,?)', (code,q['number'],base64.b64decode(q['image'])))
            q['image'] = True
    room = {'code':code, 'title':title, 'questions':questions, 'duration':duration,
            'mode':mode, 'generation':GENERATION, 'status':'waiting', 'expires_at':now()+1800,
            'players':{str(uid):player(1)}, 'started_at':None, 'deadline':None,
            'keyed':all(q.get('answer') in q['options'] for q in questions)}
    save(conn, room)
    return room

def view(room, uid):
    own = room['players'][str(uid)]
    result = {key:room[key] for key in ('code','title','duration','mode','status','expires_at','started_at','deadline','keyed')}
    result['server_now'] = now()
    result['reason'] = room.get('reason')
    result['me'] = own['alias']
    result['players'] = [{'alias':p['alias'],'ready':p['ready'],'submitted':p['submitted']} for p in room['players'].values()]
    result['answers'] = own['answers']
    result['questions'] = []
    if room['status'] in ('active','finished'):
        for q in room['questions']:
            safe = {k:q[k] for k in ('number','text','options')}
            if q.get('image'):
                safe['image_url'] = f"/api/battles/rooms/{room['code']}/images/{q['number']}"
            if room['status'] == 'finished': safe['answer'] = q.get('answer')
            result['questions'].append(safe)
    if room['status'] == 'finished':
        scores = []
        for p in room['players'].values():
            score = sum(p['answers'].get(str(q['number']),{}).get('label') == q.get('answer') for q in room['questions']) if room['keyed'] else None
            scores.append({'alias':p['alias'],'score':score, 'answered':sum(a['label'] is not None for a in p['answers'].values())})
        result['scores'] = scores
        result['outcome'] = 'Unscored practice - no winner' if not room['keyed'] else ('Draw' if scores[0]['score'] == scores[1]['score'] else max(scores,key=lambda s:s['score'])['alias'] + ' wins')
    return result

class CreateRoom(BaseModel):
    paper_id:int|None = None
    synthetic:bool = False
    duration_seconds:int|None = Field(default=None, ge=60, le=21600)
    share_confirmed:bool = False

@router.post('/rooms', status_code=201)
async def create(payload:CreateRoom, user=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    if payload.synthetic:
        if payload.paper_id is not None: raise HTTPException(422,'Choose one source.')
        questions = copy.deepcopy(SYNTHETIC['questions']); title=SYNTHETIC['title']
        duration=payload.duration_seconds or SYNTHETIC['duration_seconds']
    else:
        if not payload.share_confirmed: raise HTTPException(422,'Confirm sharing this paper snapshot with your invited opponent.')
        paper=await db.get(Paper,payload.paper_id) if payload.paper_id else None
        if not paper or paper.owner_id != user.id: raise HTTPException(404,'Paper not found')
        if paper.status != 'ready': raise HTTPException(422,'Paper is not ready')
        meta=json.loads(paper.meta or '{}'); mins=meta.get('duration_minutes')
        duration=int(float(mins)*60) if mins else payload.duration_seconds
        if not duration or not 60<=duration<=21600: raise HTTPException(422,'Choose a duration between 1 and 360 minutes.')
        qs=(await db.execute(select(Question).where(Question.paper_id==paper.id).order_by(Question.question_number))).scalars().all()
        if not qs or len(qs)>500: raise HTTPException(422,'Choose a paper with 1 to 500 questions.')
        questions=[]; total_images=0
        for q in qs:
            opts=(await db.execute(select(Option).where(Option.question_id==q.id).order_by(Option.label))).scalars().all()
            if len(opts) not in (4,5) or [o.label for o in opts]!=list('ABCDE'[:len(opts)]):
                raise HTTPException(422,'Review each question: battle supports A-D or A-E choices.')
            item={'number':q.question_number,'text':q.question_text,'options':{o.label:o.option_text for o in opts},'answer':next((o.label for o in opts if o.id==q.correct_option_id),None)}
            if q.image_url:
                match=re.fullmatch(r'/api/papers/([0-9]+)/assets/([A-Za-z0-9_.-]+)',q.image_url)
                if not match: raise HTTPException(422,'Source image must be an owned private paper asset.')
                source_paper=await db.get(Paper,int(match[1]))
                if not source_paper or source_paper.owner_id!=user.id: raise HTTPException(403,'Source image is not owned by this user.')
                source=(await db.execute(select(Question.id).where(Question.paper_id==source_paper.id,Question.image_url==q.image_url).limit(1))).first()
                if not source: raise HTTPException(422,'Source image is not linked to the owned source paper.')
                filename=match[2]
                path=Path(get_settings().upload_dir)/'questions'/filename
                if not path.is_file(): raise HTTPException(422,'A source image is unavailable; cannot create an incomplete battle.')
                data=path.read_bytes(); total_images+=len(data)
                if total_images>20_000_000: raise HTTPException(422,'Source images exceed the 20 MB battle preview limit.')
                item['image']=base64.b64encode(data).decode()
            if any(o.image_url for o in opts): raise HTTPException(422,'Separate option images are not supported in battle preview; use a complete source PDF crop.')
            questions.append(item)
        if len({q['number'] for q in questions})!=len(questions): raise HTTPException(422,'Select a paper with unique question numbers, not multiple sets.')
        title=paper.title
    with transaction() as conn:
        room=new_room(conn,user.id,title,questions,duration,'friend')
        return view(room,user.id)

@router.post('/rooms/{code}/join')
def join(code:str,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code)
        if str(user.id) in room['players']: return view(room,user.id)
        if room['mode']!='friend' or room['status']!='waiting' or len(room['players'])!=1: raise HTTPException(409,'Room cannot accept another player.')
        for raw, in conn.execute('SELECT body FROM rooms').fetchall():
            other=settle(json.loads(raw))
            if str(user.id) in other['players'] and other['status'] in ('waiting','active'): raise HTTPException(409,'Leave your current room first.')
        room['players'][str(user.id)]=player(2); save(conn,room)
        return view(room,user.id)

@router.get('/rooms/{code}')
def get_room(code:str,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); member(room,user)
        return view(room,user.id)

@router.post('/rooms/{code}/ready')
def ready(code:str,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); own=member(room,user)
        if room['status']=='waiting':
            own['ready']=True
            if len(room['players'])==2 and all(p['ready'] for p in room['players'].values()):
                room.update(status='active',started_at=now(),deadline=now()+room['duration'])
            save(conn,room)
        return view(room,user.id)

class Answer(BaseModel):
    number:int = Field(ge=1)
    label:str|None = Field(default=None,pattern='^[A-E]$')
    version:int = Field(ge=1)

@router.put('/rooms/{code}/answer')
def answer(code:str,payload:Answer,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); own=member(room,user)
        if room['status']!='active' or own['submitted']: raise HTTPException(409,'Answers are closed. Refresh the battle result.')
        q=next((q for q in room['questions'] if q['number']==payload.number),None)
        if q is None or payload.label is not None and payload.label not in q['options']: raise HTTPException(422,'Question or option not in this battle.')
        old=own['answers'].get(str(payload.number))
        if old is None or payload.version>old['version']:
            own['answers'][str(payload.number)]={'label':payload.label,'version':payload.version}
        save(conn,room)
        return view(room,user.id)

@router.post('/rooms/{code}/submit')
def submit(code:str,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); own=member(room,user)
        if room['status']=='active': own['submitted']=True; settle(room); save(conn,room)
        return view(room,user.id)

@router.post('/rooms/{code}/leave')
def leave(code:str,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); member(room,user)
        if room['status']=='waiting': room.update(status='cancelled',reason='A player left before the start. No winner.'); save(conn,room)
        elif room['status']=='active': raise HTTPException(409,'An active battle clock keeps running. You can rejoin until the deadline.')
        conn.execute('DELETE FROM queue WHERE uid=?',(user.id,))
        return view(room,user.id)

@router.get('/rooms/{code}/images/{number}')
def image(code:str,number:int,user=Depends(get_current_user)):
    with transaction() as conn:
        room=load(conn,code); member(room,user)
        if room['status'] not in ('active','finished'): raise HTTPException(404,'Image unavailable')
        q=next((q for q in room['questions'] if q['number']==number),{})
        if not q.get('image'): raise HTTPException(404,'Image not found')
        asset=conn.execute('SELECT data FROM assets WHERE code=? AND number=?',(room['code'],number)).fetchone()
        if not asset: raise HTTPException(404,'Image unavailable')
        return Response(asset[0],media_type='image/png',headers={'Cache-Control':'private, no-store'})

@router.post('/queue')
def queue(user=Depends(get_current_user)):
    """Only an explicitly synthetic, fixed 120-second development pool."""
    with transaction() as conn:
        existing=conn.execute('SELECT code FROM queue WHERE uid=?',(user.id,)).fetchone()
        if existing:
            room=load(conn,existing[0])
            if room['status'] in ('waiting','active'): return view(room,user.id)
            conn.execute('DELETE FROM queue WHERE uid=?',(user.id,))
        for uid,code in conn.execute('SELECT uid,code FROM queue WHERE uid!=? ORDER BY rowid',(user.id,)).fetchall():
            room=load(conn,code)
            if room['status'] not in ('waiting','active'):
                conn.execute('DELETE FROM queue WHERE uid=?',(uid,)); continue
            if room['status']!='waiting' or len(room['players'])!=1: continue
            for raw, in conn.execute('SELECT body FROM rooms').fetchall():
                other=settle(json.loads(raw))
                if str(user.id) in other['players'] and other['status'] in ('waiting','active'): raise HTTPException(409,'Leave your current room first.')
            room['players'][str(user.id)]=player(2); save(conn,room)
            conn.execute('INSERT OR REPLACE INTO queue VALUES (?,?)',(user.id,code))
            return view(room,user.id)
        room=new_room(conn,user.id,SYNTHETIC['title'],copy.deepcopy(SYNTHETIC['questions']),SYNTHETIC['duration_seconds'],'synthetic_queue')
        conn.execute('INSERT OR REPLACE INTO queue VALUES (?,?)',(user.id,room['code']))
        return view(room,user.id)

@router.delete('/queue')
def cancel_queue(user=Depends(get_current_user)):
    with transaction() as conn:
        row=conn.execute('SELECT code FROM queue WHERE uid=?',(user.id,)).fetchone()
        if row:
            room=load(conn,row[0]); member(room,user)
            if room['status']=='waiting': room.update(status='cancelled',reason='Queue cancelled. No winner.'); save(conn,room)
            elif room['status']=='active': raise HTTPException(409,'Already playing. The clock keeps running.')
        conn.execute('DELETE FROM queue WHERE uid=?',(user.id,))
        return {'cancelled':True}
