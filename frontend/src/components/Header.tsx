import { Link, NavLink, useNavigate } from 'react-router-dom';
import { LogOut, Moon, Sun, Sparkles, History } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

export default function Header() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();

  const linkBase =
    'px-3 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1.5';
  const linkActive = 'bg-brand-500/10 text-brand-700 dark:text-brand-300';
  const linkIdle =
    'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800';

  return (
    <header className="sticky top-0 z-30 bg-white/80 dark:bg-slate-900/80 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <Sparkles className="w-5 h-5 text-brand-500" />
          <span>AI 研究助手</span>
        </Link>

        {user && (
          <nav className="flex items-center gap-1 ml-2">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
            >
              <Sparkles className="w-4 h-4" /> 研究
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
            >
              <History className="w-4 h-4" /> 历史
            </NavLink>
          </nav>
        )}

        <div className="flex-1" />

        <button
          onClick={toggle}
          className="p-2 rounded-md text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          title={theme === 'dark' ? '切换浅色' : '切换深色'}
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {user ? (
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                logout();
                nav('/login');
              }}
              className="p-2 rounded-md text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              title="退出登录"
            >
              <LogOut className="w-5 h-5" />
            </button>
            <Link
              to="/profile"
              className="text-sm text-slate-600 dark:text-slate-300 px-2 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800"
              title="用户面板"
            >
              {user.username}
            </Link>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm rounded-md text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              登录
            </Link>
            <Link
              to="/register"
              className="px-3 py-1.5 text-sm rounded-md bg-brand-500 text-white hover:bg-brand-600"
            >
              注册
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
