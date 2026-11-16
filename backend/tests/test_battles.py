import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_paper_repair import api, account, upload_docx
from app.api.routes import battles as b

@pytest.fixture(autouse=True)
def isolated_battles(tmp_path, monkeypatch):
    monkeypatch.setenv('BATTLE_DB',str(tmp_path/'battles.sqlite'))

def post(api,h,path,data=None):
    return api.post('/api/battles'+path,headers=h,json=data)

def create(api,h,**kwargs):
    r=post(api,h,'/rooms',{'synthetic':True,**kwargs});assert r.status_code==201,r.text;return r.json()

def pair(api):
    a=account(api,'one'); z=account(api,'two'); c=create(api,a)['code']
    assert post(api,z,f'/rooms/{c}/join').status_code==200
    return a,z,c

def begin(api,a,z,c):
    assert post(api,a,f'/rooms/{c}/ready').json()['status']=='waiting'
    r=post(api,z,f'/rooms/{c}/ready'); assert r.json()['status']=='active',r.text
    return r.json()

def get(api,h,c):
    return api.get('/api/battles/rooms/'+c,headers=h)

def put(api,h,c,n,label,v=1):
    return api.put('/api/battles/rooms/'+c+'/answer',headers=h,json={'number':n,'label':label,'version':v})

def test_friend_flow_hidden_key_draw_private_answers(api):
    a,z,c=pair(api); r=begin(api,a,z,c)
    assert [len(q['options']) for q in r['questions']]==[4,5,4,5]
    assert all('answer' not in q for q in r['questions'])
    assert put(api,a,c,1,'B').status_code==200
    assert put(api,a,c,2,'E').status_code==200
    assert get(api,z,c).json()['answers']=={}
    put(api,z,c,3,'B');put(api,z,c,4,'C')
    r=post(api,a,f'/rooms/{c}/submit').json()
    assert r['status']=='active' and 'scores' not in r and 'answer' not in r['questions'][0]
    assert put(api,a,c,1,'A',2).status_code==409
    r=post(api,z,f'/rooms/{c}/submit').json()
    assert r['outcome']=='Draw' and [s['score'] for s in r['scores']]==[2,2]
    assert post(api,a,f'/rooms/{c}/submit').json()['scores']==r['scores']

def test_unauthorized_and_full_room(api):
    a,z,c=pair(api);third=account(api,'third')
    assert get(api,third,c).status_code==404
    assert post(api,third,f'/rooms/{c}/join').status_code==409
    assert post(api,third,f'/rooms/{c}/ready').status_code==404
    assert put(api,third,c,1,'A').status_code==404
    assert api.get(f'/api/battles/rooms/{c}/images/1',headers=third).status_code==404
    assert api.get(f'/api/battles/rooms/{c}').status_code==401

def test_versions_validation_and_refresh(api):
    a,z,c=pair(api);r=begin(api,a,z,c); deadline=r['deadline']
    put(api,a,c,1,'B',2);put(api,a,c,1,'A',1)
    assert get(api,a,c).json()['answers']['1']=={'label':'B','version':2}
    assert put(api,a,c,99,'A').status_code==422
    assert put(api,a,c,1,'E',3).status_code==422
    assert put(api,a,c,1,'F',3).status_code==422
    assert get(api,a,c).json()['deadline']==deadline
    assert post(api,a,f'/rooms/{c}/ready').json()['deadline']==deadline

def test_deadline_autosubmit_only_saved(api,monkeypatch):
    a,z,c=pair(api);r=begin(api,a,z,c);put(api,a,c,1,'B')
    monkeypatch.setattr(b,'now',lambda:r['deadline']+1)
    assert put(api,z,c,1,'B').status_code==409
    result=get(api,a,c).json()
    assert result['status']=='finished' and result['outcome']=='Player 1 wins'
    assert all(p['submitted'] for p in result['players'])
    assert [s['score'] for s in result['scores']]==[1,0]

def test_restart_cancels_not_loss(api,monkeypatch):
    a,z,c=pair(api);begin(api,a,z,c);put(api,a,c,1,'B')
    monkeypatch.setattr(b,'GENERATION','new-process')
    r=get(api,a,c).json()
    assert r['status']=='cancelled' and 'scores' not in r and 'winner' in r['reason']
    assert put(api,a,c,1,'B',2).status_code==409

def test_expired_room_and_only_one_active(api,monkeypatch):
    a=account(api,'one');z=account(api,'two');r=create(api,a)
    assert post(api,a,'/rooms',{'synthetic':True}).status_code==409
    monkeypatch.setattr(b,'now',lambda:r['expires_at']+1)
    assert post(api,z,f"/rooms/{r['code']}/join").status_code==409
    assert get(api,a,r['code']).json()['status']=='cancelled'

def test_queue_pair_cancel_and_no_fake_opponent(api):
    a=account(api,'one');z=account(api,'two');third=account(api,'three')
    ra=post(api,a,'/queue').json();assert len(ra['players'])==1
    rz=post(api,z,'/queue').json();assert rz['code']==ra['code'] and len(rz['players'])==2
    assert post(api,a,'/queue').json()['code']==ra['code']
    rt=post(api,third,'/queue').json();assert rt['code']!=ra['code'] and len(rt['players'])==1
    assert api.delete('/api/battles/queue',headers=third).json()=={'cancelled':True}
    assert get(api,third,rt['code']).json()['status']=='cancelled'
    assert post(api,third,f"/rooms/{ra['code']}/join").status_code==409
    begin(api,a,z,ra['code'])
    assert api.delete('/api/battles/queue',headers=a).status_code==409

def test_concurrent_join_and_ready_single_start(api):
    a=account(api,'one');z=account(api,'two');third=account(api,'third');c=create(api,a)['code']
    with ThreadPoolExecutor(2) as pool:
        statuses=list(pool.map(lambda h:post(api,h,f'/rooms/{c}/join').status_code,[z,third]))
    assert sorted(statuses)==[200,409]
    opponent=z if statuses[0]==200 else third
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda h:post(api,h,f'/rooms/{c}/ready').status_code,[a,opponent]))
    r=get(api,a,c).json(); assert r['status']=='active'
    assert post(api,a,f'/rooms/{c}/ready').json()['started_at']==r['started_at']

def test_unkeyed_uploaded_paper_snapshot_and_scope(api):
    import asyncio
    from app.models.question import Question
    from sqlalchemy import select
    import app.db as dbmod
    a=account(api,'one');z=account(api,'two');third=account(api,'third')
    paper=upload_docx(api,a,keyed=False)
    # upload helper returns id
    pid=paper['id'] if isinstance(paper,dict) else paper
    r=post(api,a,'/rooms',{'paper_id':pid,'duration_seconds':60,'share_confirmed':True})
    assert r.status_code==201,r.text
    c=r.json()['code'];post(api,z,f'/rooms/{c}/join');start=begin(api,a,z,c)
    assert not start['keyed']
    async def edit_source():
        async with dbmod.SessionLocal() as db:
            q=(await db.execute(select(Question).where(Question.paper_id==pid))).scalars().first()
            q.question_text='Changed later';await db.commit()
    asyncio.run(edit_source())
    assert get(api,a,c).json()['questions'][0]['text']!='Changed later'
    assert api.get(f'/api/papers/{pid}/questions',headers=z).status_code==403
    put(api,a,c,1,'B');post(api,a,f'/rooms/{c}/submit');end=post(api,z,f'/rooms/{c}/submit').json()
    assert 'no winner' in end['outcome'] and all(s['score'] is None for s in end['scores'])
    assert post(api,third,'/rooms',{'paper_id':pid,'share_confirmed':True}).status_code==404

def test_frozen_private_image_and_old_room_recreation(api):
    import asyncio
    import base64
    from pathlib import Path
    from app.config import get_settings
    from app.models.question import Question
    import app.db as dbmod
    from sqlalchemy import select
    a=account(api,'one');z=account(api,'two');third=account(api,'third')
    pid=upload_docx(api,a)
    img=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jC1kAAAAASUVORK5CYII=')
    path=Path(get_settings().upload_dir)/'questions'/'test-source.png';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(img)
    async def set_image():
        async with dbmod.SessionLocal() as db:
            q=(await db.execute(select(Question).where(Question.paper_id==pid))).scalars().first()
            q.image_url=f'/api/papers/{pid}/assets/test-source.png';await db.commit()
    asyncio.run(set_image())
    r=post(api,a,'/rooms',{'paper_id':pid,'duration_seconds':60,'share_confirmed':True});assert r.status_code==201
    c=r.json()['code'];post(api,z,f'/rooms/{c}/join');start=begin(api,a,z,c)
    url=start['questions'][0]['image_url'];path.unlink() # original disappears; frozen copy must survive
    assert api.get(url,headers=z).content==img
    assert api.get(url,headers=third).status_code==404
    assert api.get(f'/api/papers/{pid}/assets/test-source.png',headers=z).status_code==403
    post(api,a,f'/rooms/{c}/submit');post(api,z,f'/rooms/{c}/submit')
    assert create(api,a)['code']!=c # Must not loop when old finished room exists.


def test_concurrent_stranger_pairing_no_double_booking(api):
    users=[account(api,f'p{i}') for i in range(4)]
    with ThreadPoolExecutor(4) as pool:
        rooms=list(pool.map(lambda h:post(api,h,'/queue').json(),users))
    codes={r['code'] for r in rooms};assert len(codes)==2
    for code in codes:
        members=[h for h,r in zip(users,rooms) if r['code']==code]
        assert len(members)==2
        assert len(get(api,members[0],code).json()['players'])==2

def test_cannot_share_foreign_image_by_editing_own_question(api):
    import asyncio
    from app.models.question import Question
    import app.db as dbmod
    from sqlalchemy import select
    a=account(api,'one');z=account(api,'two')
    first=upload_docx(api,a);second=upload_docx(api,z)
    async def set_foreign_reference():
        async with dbmod.SessionLocal() as db:
            q=(await db.execute(select(Question).where(Question.paper_id==first))).scalars().first()
            q.image_url=f'/api/papers/{second}/assets/foreign.png';await db.commit()
    asyncio.run(set_foreign_reference())
    assert post(api,a,'/rooms',{'paper_id':first,'duration_seconds':60,'share_confirmed':True}).status_code==403
