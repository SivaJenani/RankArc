import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import './styles.css';
import Navbar from './components/Navbar';
import ThemeToggle from './components/ThemeToggle';
import ProtectedRoute from './components/ProtectedRoute';
import Battle from './pages/Battle';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import PaperSetPicker from './pages/PaperSetPicker';
import PaperReview from './pages/PaperReview';
import TestScreen from './pages/TestScreen';
import Results from './pages/Results';
import History from './pages/History';
import { DEMO_MODE, resetDemo } from './api/demo';

function DemoNavbar() {
  return <><nav className="bg-nav text-invfg border-b border-deeptext px-4 py-3"><div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
    <Link to="/" className="font-black text-xl text-accent">RankArc <span className="text-sm text-invfg">sample demo</span></Link>
    <div className="flex items-center gap-4 text-sm"><ThemeToggle/><Link to="/dashboard">My Papers</Link><Link to="/history">History</Link></div>
  </div></nav><aside className="bg-accent/10 border-b border-accent/30 text-fg px-4 py-3 text-xs"><div className="max-w-5xl mx-auto flex flex-wrap gap-3 justify-between items-center"><p className="max-w-3xl">SAMPLE DEMO: synthetic questions only. No login, AI extraction, server uploads or personal data. Demo edits and results stay in this tab. Closing the tab or resetting clears them.</p><button onClick={resetDemo} className="text-deeptext border border-deeptext rounded-lg px-3 py-2">Reset demo</button></div></aside></>;
}
function DemoUpload() {
  const navigate=useNavigate();
  return <main className="min-h-screen bg-page text-fg px-4 py-10"><section className="max-w-xl mx-auto space-y-5"><h1 className="text-3xl font-black">Upload Paper</h1><div className="bg-card border border-fg/10 p-6 rounded-2xl space-y-4"><h2 className="m-0 text-xl font-bold text-fg">Try the sample paper</h2><p className="text-muted">This demo uses ten built-in arithmetic questions. No file is uploaded or extracted. Real-file processing is not part of this login-free demo.</p><p className="text-sm text-muted">Open the sample, review or edit questions, choose the sample shift, take a timed mock test, then inspect the score and answer breakdown.</p><button className="bg-accent text-onaccent px-5 py-3 rounded-xl font-bold" onClick={()=>navigate('/papers/900001/sets')}>Load sample paper</button></div></section></main>;
}
function DemoAccountNotice() {
  return <main className="min-h-screen bg-page text-fg px-4 py-10"><section className="max-w-xl mx-auto bg-card border border-fg/10 rounded-2xl p-6 space-y-4"><h1 className="text-3xl font-black">No account needed</h1><p className="text-muted">You are exploring sample mode. It never signs in to or changes a real account.</p><Link className="inline-block bg-accent text-onaccent px-4 py-3 rounded-xl font-bold" to="/dashboard">Explore sample papers</Link></section></main>;
}
function App() {
 return <BrowserRouter basename={DEMO_MODE ? '/demo' : undefined}>
  {DEMO_MODE ? <DemoNavbar/> : <Navbar/>}
  {!DEMO_MODE && <aside className="bg-accent/10 text-fg px-4 py-3 text-center text-sm">Want to explore without login? <a className="text-deeptext font-bold underline" href="/demo/dashboard">Open the sample demo</a>. Repair preview: files, accounts and results use temporary storage and can disappear on restart. Keep originals. Use non-sensitive test papers only.</aside>}
  <Routes>
   <Route path="/" element={<Landing/>}/>
   <Route path="/login" element={DEMO_MODE ? <DemoAccountNotice/> : <Login/>}/>
   <Route path="/register" element={DEMO_MODE ? <DemoAccountNotice/> : <Register/>}/>
   {DEMO_MODE ? <>
    <Route path="/dashboard" element={<Dashboard/>}/><Route path="/upload" element={<DemoUpload/>}/>
    <Route path="/papers/:paperId/sets" element={<PaperSetPicker/>}/><Route path="/papers/:id/review" element={<PaperReview/>}/>
    <Route path="/test/:attemptId" element={<TestScreen/>}/><Route path="/results/:attemptId" element={<Results/>}/><Route path="/history" element={<History/>}/>
   </> : <Route element={<ProtectedRoute/>}>
    <Route path="/battle" element={<Battle/>}/><Route path="/battle/:code" element={<Battle/>}/>
    <Route path="/dashboard" element={<Dashboard/>}/><Route path="/upload" element={<Upload/>}/>
    <Route path="/papers/:paperId/sets" element={<PaperSetPicker/>}/><Route path="/papers/:id/review" element={<PaperReview/>}/>
    <Route path="/test/:attemptId" element={<TestScreen/>}/><Route path="/results/:attemptId" element={<Results/>}/><Route path="/history" element={<History/>}/>
   </Route>}
   <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes><Toaster position="top-right" toastOptions={{style:{fontFamily:'Inter, sans-serif',fontWeight:600,fontSize:'14px',borderRadius:'12px'},success:{duration:3000},error:{duration:5000}}}/>
 </BrowserRouter>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
