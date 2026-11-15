import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { register as registerApi, login as loginApi, getMe } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error('Please fill in all fields.');
      return;
    }
    if (password.length < 6) {
      toast.error('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    try {
      await registerApi(email, password, name);
      // Auto-login after register
      const { access_token } = await loginApi(email, password);
      localStorage.setItem('rankly_token', access_token);
      const user = await getMe();
      login(access_token, user);
      toast.success(`Welcome to Rankly, ${user.name}!`);
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Registration failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-page flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-12 h-12 bg-nav rounded-2xl flex items-center justify-center font-black text-accent text-2xl border border-deeptext shadow-md">
              R
            </div>
          </div>
          <h1 className="text-3xl font-black text-fg tracking-tight">Create account</h1>
          <p className="text-muted mt-2 font-medium">Join Rankly and start practicing</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-card/90 backdrop-blur border border-fg/10 rounded-3xl p-8 shadow-xl space-y-5"
        >
          <div>
            <label className="block text-sm font-bold text-fg mb-1.5">Full Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Arjun Sharma"
              className="w-full px-4 py-3 rounded-xl border border-fg/20 bg-card focus:outline-none focus:ring-2 focus:ring-accent focus:border-deeptext text-fg placeholder-muted/60 font-medium transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-fg mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-4 py-3 rounded-xl border border-fg/20 bg-card focus:outline-none focus:ring-2 focus:ring-accent focus:border-deeptext text-fg placeholder-muted/60 font-medium transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-fg mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 6 characters"
              className="w-full px-4 py-3 rounded-xl border border-fg/20 bg-card focus:outline-none focus:ring-2 focus:ring-accent focus:border-deeptext text-fg font-medium transition-all"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-accent hover:bg-accenth text-onaccent font-black rounded-xl transition-all shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2 justify-center">
                <svg className="w-4 h-4 animate-spin text-fg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating account…
              </span>
            ) : (
              'Create Account'
            )}
          </button>

          <p className="text-center text-sm text-muted">
            Already have an account?{' '}
            <Link to="/login" className="text-deeptext font-black hover:text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
