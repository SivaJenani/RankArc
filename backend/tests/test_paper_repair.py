"""Regression coverage. Real-paper test is opt-in and never embeds the paper in git."""
import io
import json
import os
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.services.local_extractor import extract_questions
from app.services.parser import extract_text_from_docx


def test_multiline_parentheses_and_unknown_answers():
    meta, qs = extract_questions('''Practice
Duration: 10 minutes
1. Calculate f(x) correctly?
(A) 2 (two)
continued text
(B) 4 (four)
(C) 6
(D) 8
(E) None
2. Choose the second letter?
A. A B. B C. C D. D
Answer: B
''')
    assert len(qs) == 2
    assert len(qs[0]['options']) == 5 and len(qs[1]['options']) == 4
    assert qs[0]['options'][0]['option_text'] == '2 (two)\ncontinued text'
    assert not any(o['is_correct'] for o in qs[0]['options'])
    assert qs[1]['options'][1]['is_correct']
    assert meta['unkeyed_questions'] == 1
    assert meta['paper_sets'][0]['q_count'] == 2


def test_no_silent_partial_test():
    with pytest.raises(ValueError, match='question'):
        extract_questions('1. Complete?\n(A) yes (B) no\n2. Broken?\n(A) only one')


def test_docx_tables_preserve_order(tmp_path):
    doc = Document(); doc.add_paragraph('1. Read this table?')
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = '(A) first'; table.cell(0, 1).text = '(B) second'
    doc.add_paragraph('Answer: B')
    path = tmp_path / 'paper.docx'; doc.save(path)
    text = extract_text_from_docx(str(path))
    _, qs = extract_questions(text)
    assert len(qs) == 1 and qs[0]['options'][1]['is_correct']


@pytest.fixture
def api(tmp_path, monkeypatch):
    import asyncio
    import app.db as dbmod
    from app.models.base import Base
    from app.main import app
    from app.db import get_db
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/test.db')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(setup())
    async def override():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(dbmod, 'SessionLocal', sessions)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), 'upload_dir', str(tmp_path / 'uploads'))
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def account(client, name):
    import secrets
    r = client.post('/api/auth/register', json={'email': f'{name}@example.com', 'name': name, 'password': secrets.token_urlsafe(18)})
    assert r.status_code == 201, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


def upload_docx(client, headers, keyed=True):
    doc = Document(); doc.add_paragraph('Synthetic Practice')
    for i in range(1, 4):
        doc.add_paragraph(f'{i}. What is two plus two?')
        doc.add_paragraph('(A) 3 (B) 4 (C) 5 (D) 6')
        if keyed: doc.add_paragraph('Answer: B')
    buf = io.BytesIO(); doc.save(buf)
    r = client.post('/api/papers/upload', headers=headers, files={'file': ('paper.docx', buf.getvalue())}, data={'title':'Synthetic'})
    assert r.status_code == 201, r.text
    pid = r.json()['id']
    status = client.get(f'/api/papers/{pid}/status', headers=headers).json()
    assert status['status'] == 'ready', status
    return pid


def test_full_flow_and_ownership(api):
    a, b = account(api, 'a'), account(api, 'b')
    pid = upload_docx(api, a)
    meta = api.get(f'/api/papers/{pid}/meta', headers=a).json()
    assert meta['paper_sets'][0]['q_count'] == 3
    qs = api.get(f'/api/papers/{pid}/questions', headers=a).json()
    q = qs[0]
    ids = [o['id'] for o in q['options']]
    payload = {'question_text': q['question_text'] + ' Updated', 'options': q['options'], 'correct_option_id': ids[1]}
    edited = api.put(f'/api/papers/{pid}/questions/{q["id"]}', headers=a, json=payload)
    assert edited.status_code == 200, edited.text
    assert [o['id'] for o in edited.json()['options']] == ids
    assert edited.json()['correct_option_id'] == ids[1]
    assert api.post(f'/api/attempts/start/{pid}', headers=b).status_code == 404
    assert api.get(f'/api/papers/{pid}/questions', headers=b).status_code == 403
    start = api.post(f'/api/attempts/start/{pid}', headers=a).json()
    assert all(q['correct_option_id'] is None and not any(o['is_correct'] for o in q['options']) for q in start['questions'])
    aid = start['attempt_id']
    foreign_pid = upload_docx(api, b)
    foreign = api.get(f'/api/papers/{foreign_pid}/questions', headers=b).json()[0]
    route = f'/api/attempts/{aid}/submit'
    assert api.post(route, headers=a, json={'answers':[{'question_id':foreign['id'],'selected_option_id':None}]}).status_code == 422
    assert api.post(route, headers=a, json={'answers':[{'question_id':q['id'],'selected_option_id':foreign['options'][0]['id']}]}).status_code == 422
    assert api.post(route, headers=a, json={'answers':[{'question_id':q['id']},{'question_id':q['id']}]}).status_code == 422
    answers = [{'question_id':qs[0]['id'],'selected_option_id':ids[1]},
               {'question_id':qs[1]['id'],'selected_option_id':qs[1]['options'][0]['id']}]
    submitted = api.post(route, headers=a, json={'answers':answers})
    assert submitted.status_code == 200, submitted.text
    assert round(submitted.json()['score'], 2) == 33.33
    result = api.get(f'/api/attempts/{aid}/result', headers=a).json()
    assert len(result['answers']) == 3
    assert [i['is_correct'] for i in result['answers']] == [True, False, None]
    assert api.get(f'/api/attempts/{aid}/result', headers=b).status_code == 403
    assert api.post(route, headers=a, json={'answers':answers}).status_code == 409
    assert api.put(f'/api/papers/{pid}/questions/{q["id"]}', headers=a, json=payload).status_code == 409


def test_unkeyed_practice_is_not_falsely_scored(api):
    a = account(api, 'practice'); pid = upload_docx(api, a, keyed=False)
    start = api.post(f'/api/attempts/start/{pid}', headers=a).json()
    q = start['questions'][0]
    r = api.post(f'/api/attempts/{start["attempt_id"]}/submit', headers=a,
                 json={'answers':[{'question_id':q['id'],'selected_option_id':q['options'][0]['id']}]})
    assert r.status_code == 200 and r.json()['score'] is None
    res = api.get(f'/api/attempts/{start["attempt_id"]}/result', headers=a).json()
    assert res['answers'][0]['is_correct'] is None


def test_bad_uploads(api):
    a = account(api, 'upload')
    for filename, data in [('old.doc', b'bad'),('empty.pdf',b'')]:
        assert api.post('/api/papers/upload', headers=a, files={'file':(filename,data)}).status_code == 422
    r = api.post('/api/papers/upload', headers=a, files={'file':('broken.pdf',b'not a PDF')})
    assert r.status_code == 201
    state = api.get(f'/api/papers/{r.json()["id"]}/status', headers=a).json()
    assert state['status'] == 'failed'
    assert 'valid PDF' in state['step']


@pytest.mark.skipif(not os.getenv('RANKLY_TEST_PDF'), reason='Private PDF provided only explicitly at test time')
def test_actual_scan_upload_and_private_images(api):
    a, b = account(api,'scan-a'), account(api,'scan-b')
    with open(os.environ['RANKLY_TEST_PDF'],'rb') as f:
        r=api.post('/api/papers/upload',headers=a,files={'file':('scan.pdf',f,'application/pdf')},data={'title':'Private scan QA'})
    assert r.status_code == 201, r.text
    pid=r.json()['id']
    state=api.get(f'/api/papers/{pid}/status',headers=a).json()
    assert state['status']=='ready',state
    qs=api.get(f'/api/papers/{pid}/questions',headers=a).json()
    assert [q['question_number'] for q in qs]==list(range(1,101))
    assert all([o['label'] for o in q['options']]==list('ABCDE') for q in qs)
    assert all(q['correct_option_id'] is None for q in qs)
    image=qs[0]['image_url']
    assert api.get(image,headers=a).status_code==200
    assert api.get(image).status_code==401
    assert api.get(image,headers=b).status_code==403
    assert api.get('/uploads/questions/'+image.split('/')[-1]).status_code==404
    assert api.get(f'/api/papers/{pid}/assets/not-real.png',headers=a).status_code==404
    start=api.post(f'/api/attempts/start/{pid}',headers=a).json()
    assert len(start['questions'])==100 and start['duration_seconds']==10800
    r=api.post(f'/api/attempts/{start["attempt_id"]}/submit',headers=a,json={'answers':[]})
    assert r.status_code==200 and r.json()['score'] is None
    result=api.get(f'/api/attempts/{start["attempt_id"]}/result',headers=a).json()
    assert len(result['answers'])==100


def test_searchable_pdf_graphics_preserved_and_inline_key(api, tmp_path):
    import fitz
    from app.services.llm_extractor import _read_document
    from app.config import get_settings
    doc = fitz.open(); p = doc.new_page()
    p.insert_text((45, 60), '1. Identify the pictured shape?')
    p.draw_rect(fitz.Rect(50, 80, 130, 130), color=(0, 0, 0))
    p.insert_text((45, 160), '(A) Circle (B) Square (C) Triangle (D) Oval')
    p.insert_text((45, 185), 'Answer: B')
    path = tmp_path / 'graphics.pdf'; doc.save(path); doc.close()
    meta, qs = _read_document(str(path), 987, get_settings())
    assert len(qs) == 1 and len(qs[0]['options']) == 4
    assert qs[0]['options'][1]['is_correct']
    assert qs[0]['image_url'] and meta['unkeyed_questions'] == 0


def test_separate_key_review_apply_copy_and_ownership(api):
    a, b = account(api, 'keyowner'), account(api, 'keyother')
    pid = upload_docx(api, a, keyed=False)
    key = b'Answer key\n1 B\n2 A\n3 D\n'
    route = f'/api/papers/{pid}/answer-key'
    assert api.post(route+'/preview', headers=b, files={'file':('key.txt',key)}).status_code == 403
    preview = api.post(route+'/preview', headers=a, files={'file':('key.txt',key)})
    assert preview.status_code == 200, preview.text
    p = preview.json(); assert not p['errors']
    entries = [{k:e[k] for k in ['number','label']} for e in p['entries']]
    payload = {'entries':entries,'fingerprint':p['fingerprint'],'confirmed':False}
    assert api.post(route+'/apply',headers=a,json=payload).status_code == 422
    payload['confirmed']=True
    assert api.post(route+'/apply',headers=b,json=payload).status_code == 403
    payload['fingerprint']='stale'
    assert api.post(route+'/apply',headers=a,json=payload).status_code == 409
    payload['fingerprint']=p['fingerprint']
    # Existing unkeyed result must stay unchanged after a key is applied.
    attempt = api.post(f'/api/attempts/start/{pid}',headers=a).json()
    q=attempt['questions'][0]
    submitted=api.post(f'/api/attempts/{attempt["attempt_id"]}/submit',headers=a,json={'answers':[{'question_id':q['id'],'selected_option_id':q['options'][1]['id']}]})
    assert submitted.json()['score'] is None
    applied=api.post(route+'/apply',headers=a,json=payload)
    assert applied.status_code==200,applied.text
    copy_id=applied.json()['paper_id']; assert copy_id!=pid
    original=api.get(f'/api/papers/{pid}/questions',headers=a).json()
    copied=api.get(f'/api/papers/{copy_id}/questions',headers=a).json()
    assert all(q['correct_option_id'] is None for q in original)
    assert all(q['correct_option_id'] is not None for q in copied)
    past=api.get(f'/api/attempts/{attempt["attempt_id"]}/result',headers=a).json()
    assert past['attempt']['score'] is None
    new_attempt=api.post(f'/api/attempts/start/{copy_id}',headers=a).json()
    answers=[]
    for q,label in zip(new_attempt['questions'],['B','A','D']):
        assert q['correct_option_id'] is None
        answers.append({'question_id':q['id'],'selected_option_id':next(o['id'] for o in q['options'] if o['label']==label)})
    score=api.post(f'/api/attempts/{new_attempt["attempt_id"]}/submit',headers=a,json={'answers':answers})
    assert score.json()['score']==100
    for bad in [b'1 B\n1 B\n2 A\n3 D',b'1 B\n2 E\n3 D',b'1 A\n2 B',b'1 A\n2 B\n3 D\n4 A']:
        response=api.post(route+'/preview',headers=a,files={'file':('key.txt',bad)})
        assert response.status_code==200 and response.json()['errors']


def test_scanned_answer_key_ocr(tmp_path):
    from PIL import Image,ImageDraw,ImageFont
    from app.services.answer_keys import read_key,parse_key
    image=Image.new('RGB',(800,450),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
    draw.multiline_text((40,40),'Answer Key\n1 B\n2 A\n3 D',font=font,fill='black',spacing=14)
    path=tmp_path/'key.png';image.save(path)
    assert parse_key(read_key(str(path)))==[{'number':1,'label':'B'},{'number':2,'label':'A'},{'number':3,'label':'D'}]
