import { AxiosError, type AxiosAdapter } from 'axios';

export const DEMO_MODE = location.pathname === '/demo' || location.pathname.startsWith('/demo/');
const KEY = 'rankly_demo_v1';
const paperId = 900001;
const title = 'Sample arithmetic practice (synthetic demo)';
const label = 'Sample shift';
const freshQuestions = () => Array.from({length:10}, (_,i) => ({
  id:1001+i, question_number:i+1, question_text:`What is ${i+1} + ${i+1}?`,
  question_type:'mcq', paper_set:label, correct_option_id:(i+1)*10+2,
  explanation:`${i+1} + ${i+1} = ${(i+1)*2}.`, image_url:null,
  options:['A','B','C','D'].map((l,j)=>({id:(i+1)*10+j+1,label:l,option_text:String((i+1)*2+j-1),is_correct:j===1})),
}));
interface DemoState { questions:any[]; attempts:any[]; next:number }
function load(): DemoState {
  try {const saved=JSON.parse(sessionStorage.getItem(KEY)||'null'); if(saved?.questions?.length && Array.isArray(saved.attempts)) return saved;} catch { /* start fresh */ }
  return {questions:freshQuestions(),attempts:[],next:1};
}
const state=load();
const save=()=>sessionStorage.setItem(KEY,JSON.stringify(state));
export function resetDemo() {sessionStorage.removeItem(KEY);sessionStorage.removeItem('rankly_demo_test');location.assign('/demo/dashboard');}

// This adapter is used only under /demo. It never forwards a request to the API.
export const demoAdapter: AxiosAdapter = async config => {
  const path=(config.url||'').split('?')[0];
  const method=(config.method||'get').toLowerCase();
  const payload=typeof config.data==='string' ? JSON.parse(config.data||'{}') : (config.data||{});
  const response=(data:any,status=200)=>({data,status,statusText:status===200?'OK':'Created',headers:{},config});
  const fail=(message:string,status=404):never=>{throw new AxiosError(message,'DEMO_REQUEST',config,undefined,response({detail:message},status));};
  if(path==='/api/papers/' && method==='get') return response([{id:paperId,title,status:'ready',question_count:state.questions.length,created_at:new Date().toISOString(),filename:'synthetic-sample.docx'}]);
  if(path===`/api/papers/${paperId}/meta`) return response({paper_id:paperId,title,exam_title:title,categories:[{name:'Addition basics I',q_start:1,q_end:3,count:3},{name:'Addition basics II',q_start:4,q_end:6,count:3},{name:'Addition practice I',q_start:7,q_end:8,count:2},{name:'Addition practice II',q_start:9,q_end:10,count:2}],paper_sets:[{label,q_count:10}],duration_minutes:10});
  if(path===`/api/papers/${paperId}/questions` && method==='get') return response(state.questions);
  const edit=path.match(new RegExp(`^/api/papers/${paperId}/questions/(\\d+)$`));
  if(edit && method==='put') {
    const q=state.questions.find(q=>q.id===Number(edit[1])); if(!q) return fail('Sample question not found.');
    if(payload.question_text!==undefined)q.question_text=payload.question_text;
    if(payload.correct_option_id!==undefined)q.correct_option_id=payload.correct_option_id;
    if(payload.options)q.options=q.options.map((o:any,i:number)=>({...o,option_text:payload.options[i]?.option_text ?? o.option_text,is_correct:o.id===q.correct_option_id}));
    save(); return response(q);
  }
  if(path===`/api/attempts/start/${paperId}` && method==='post') {
    const id=state.next++;const started_at=new Date().toISOString();
    state.attempts.push({id,paper_id:paperId,paper_title:title,started_at,submitted_at:null,status:'in_progress',score:null,total_questions:10,answers:[],snapshot:structuredClone(state.questions)});
    save();return response({attempt_id:id,paper_id:paperId,started_at,total_questions:10,duration_seconds:600,questions:state.questions.map(q=>({...q,correct_option_id:null,explanation:null,options:q.options.map((o:any)=>({...o,is_correct:false}))}))},201);
  }
  if(path==='/api/attempts/history') return response([...state.attempts].reverse().map(({answers,snapshot,...a})=>a));
  const attemptMatch=path.match(/^\/api\/attempts\/(\d+)\/(submit|result)$/);
  if(attemptMatch) {
    const a=state.attempts.find(a=>a.id===Number(attemptMatch[1])); if(!a)return fail('No sample attempt here yet. Start a sample test from My Papers.');
    if(attemptMatch[2]==='submit' && method==='post') {
      if(a.status==='completed')return fail('This sample attempt is already submitted.',409);
      a.answers=a.snapshot.map((q:any)=>{const answer=payload.answers?.find((x:any)=>x.question_id===q.id);const selected=answer?.selected_option_id??null;return {question_id:q.id,question_number:q.question_number,question_text:q.question_text,image_url:null,options:q.options,correct_option_id:q.correct_option_id,selected_option_id:selected,is_correct:selected===null?null:selected===q.correct_option_id,explanation:q.explanation,time_spent:answer?.time_spent_seconds||0};});
      a.score=a.answers.filter((x:any)=>x.is_correct).length/10*100;a.status='completed';a.submitted_at=new Date().toISOString();save();return response({id:a.id,status:a.status});
    }
    if(attemptMatch[2]==='result' && method==='get') {
      if(a.status!=='completed')return fail('Submit the sample test to see its result.',422);
      const {answers,snapshot,...attempt}=a;return response({attempt,answers});
    }
  }
  return fail('Sample mode does not upload files or access real accounts. Use the provided synthetic sample only.',403);
};
