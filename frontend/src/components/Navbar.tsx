import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Navbar() {
  const { user, token, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-[#000000] border-b border-[#253900] shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-[#08CB00] rounded-lg flex items-center justify-center font-black text-[#000000] text-lg group-hover:scale-105 transition-transform">
            R
          </div>
          <span className="text-[#EEEEEE] font-extrabold text-lg tracking-tight">rankly</span>
        </Link>

        {/* Nav Links */}
        <div className="flex items-center gap-3">
          {token ? (
            <>
              <Link
                to="/dashboard"
                className="text-[#EEEEEE] hover:text-[#08CB00] text-sm font-medium transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/history"
                className="text-[#EEEEEE] hover:text-[#08CB00] text-sm font-medium transition-colors"
              >
                History
              </Link>
              <span className="text-[#EEEEEE]/50 text-sm hidden sm:block">
                {user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm bg-[#08CB00] hover:bg-[#07b000] text-[#000000] px-3.5 py-1.5 rounded-lg font-bold transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-[#EEEEEE] hover:text-[#08CB00] text-sm font-medium transition-colors"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="text-sm bg-[#08CB00] hover:bg-[#07b000] text-[#000000] px-3.5 py-1.5 rounded-lg font-bold transition-colors"
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
