import { useEffect, useState } from 'react';

type Theme = 'dark' | 'light';

function current(): Theme {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(current);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('rankly_theme', theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return (
    <button
      type="button"
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="!p-0 w-8 h-8 !rounded-lg !bg-transparent border border-invfg/30 text-invfg hover:!bg-invfg/10 flex items-center justify-center text-base leading-none"
    >
      {theme === 'dark' ? '☀' : '☾'}
    </button>
  );
}
