import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      nav('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto mt-16 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
      <h2 className="text-xl font-semibold mb-1">登录</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
        用户名 + 密码登录账号
      </p>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <label className="text-sm">
          用户名
          <input
            className="mt-1 w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label className="text-sm">
          密码
          <input
            type="password"
            className="mt-1 w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && (
          <div className="text-sm text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 px-3 py-2 rounded">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="mt-2 w-full py-2 rounded-md bg-brand-500 hover:bg-brand-600 text-white flex items-center justify-center gap-1 disabled:bg-slate-400"
        >
          <LogIn className="w-4 h-4" /> {submitting ? '登录中...' : '登录'}
        </button>
      </form>
      <p className="text-sm text-slate-500 dark:text-slate-400 mt-4">
        还没有账号？{' '}
        <Link to="/register" className="text-brand-600 dark:text-brand-300 underline">
          去注册
        </Link>
      </p>
    </div>
  );
}
