import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(username, password, email || undefined);
      nav('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto mt-16 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
      <h2 className="text-xl font-semibold mb-1">创建账号</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
        注册后可使用研究助手并查看历史记录
      </p>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <label className="text-sm">
          用户名（2-32 位）
          <input
            className="mt-1 w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={2}
            maxLength={32}
            autoFocus
          />
        </label>
        <label className="text-sm">
          密码（至少 6 位）
          <input
            type="password"
            className="mt-1 w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>
        <label className="text-sm">
          默认邮箱（可选，用于邮件投递场景）
          <input
            type="email"
            className="mt-1 w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
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
          <UserPlus className="w-4 h-4" /> {submitting ? '注册中...' : '注册'}
        </button>
      </form>
      <p className="text-sm text-slate-500 dark:text-slate-400 mt-4">
        已有账号？{' '}
        <Link to="/login" className="text-brand-600 dark:text-brand-300 underline">
          去登录
        </Link>
      </p>
    </div>
  );
}
