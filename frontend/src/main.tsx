import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import './styles.css';

import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

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

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          {/* New: paper set picker shown after upload completes */}
          <Route path="/papers/:paperId/sets" element={<PaperSetPicker />} />
          <Route path="/papers/:id/review" element={<PaperReview />} />
          <Route path="/test/:attemptId" element={<TestScreen />} />
          <Route path="/results/:attemptId" element={<Results />} />
          <Route path="/history" element={<History />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
            fontSize: '14px',
            borderRadius: '12px',
          },
          success: { duration: 3000 },
          error: { duration: 5000 },
        }}
      />
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
