import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Landing() {
  const { token } = useAuthStore();

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">PRACTICE WITH PRECISION</p>
        <h1>Your paper.<br /><em>Your rank.</em></h1>
        <p className="lede">
          RankArc turns exam papers into timed, honest mock tests with AI-powered question
          extraction and scoring you can trust.
        </p>
        <div className="actions">
          {token ? (
            <>
              <Link to="/dashboard">
                <button>Go to Dashboard <span>→</span></button>
              </Link>
              <Link to="/upload">
                <button className="secondary">Upload a paper</button>
              </Link>
            </>
          ) : (
            <>
              <Link to="/register">
                <button>Get started free <span>→</span></button>
              </Link>
              <Link to="/login">
                <button className="secondary">Sign in</button>
              </Link>
            </>
          )}
        </div>
      </section>

      <section className="preview" aria-label="RankArc product preview">
        <div>
          <span className="kicker">NEET · 2024</span>
          <span className="ready">READY</span>
        </div>
        <h2>180 questions</h2>
        <div className="stats">
          <span><strong>+4</strong> correct</span>
          <span><strong>−1</strong> wrong</span>
          <span><strong>0</strong> blank</span>
        </div>
        <footer>
          <span>AI-parsed test</span>
          <strong>03:00:00</strong>
        </footer>
      </section>

      <section className="steps">
        <div><b>01</b><span>Upload</span></div>
        <div><b>02</b><span>Review</span></div>
        <div><b>03</b><span>Test</span></div>
      </section>
    </main>
  );
}
