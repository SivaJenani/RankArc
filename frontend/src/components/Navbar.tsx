import { Link, useNavigate } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import { useAuthStore } from '../store/authStore';

export default function Navbar() {
  const { user, token, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-nav border-b border-deeptext shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-14 py-3 flex flex-wrap gap-3 items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center font-black text-onaccent text-lg group-hover:scale-105 transition-transform">
            R
          </div>
          <span className="text-invfg font-extrabold text-lg tracking-tight">RankArc</span>
        </Link>

        {/* Nav Links */}
        <div className="flex flex-wrap justify-end items-center gap-3">
          <ThemeToggle />
          {token && <Link className="text-invfg text-sm" to="/battle">Battle</Link>}
          {token ? (
            <>
              <Link
                to="/dashboard"
                className="text-invfg hover:text-accent text-sm font-medium transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/history"
                className="text-invfg hover:text-accent text-sm font-medium transition-colors"
              >
                History
              </Link>
              <span className="text-invfg/50 text-sm hidden sm:block">
                {user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm bg-accent hover:bg-accenth text-onaccent px-3.5 py-1.5 rounded-lg font-bold transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-invfg hover:text-accent text-sm font-medium transition-colors"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="text-sm bg-accent hover:bg-accenth text-onaccent px-3.5 py-1.5 rounded-lg font-bold transition-colors"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
