import { FormEvent, useState } from 'react';
import { Save, Mail, User as UserIcon } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function ProfilePage() {
  const { user, updateEmail } = useAuth();
  const [email, setEmail] = useState(user?.email || '');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (!user) return null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    setErr(null);
    try {
      await updateEmail(email.trim());
      setMsg('已保存');
    } catch (e) {
      setErr(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-8">
      <h2 className="text-xl font-semibold mb-1">用户面板</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
        管理个人信息与默认偏好
      </p>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 mb-4">
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <UserIcon className="w-4 h-4 text-brand-500" /> 账号信息
        </h3>
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div className="text-slate-500 dark:text-slate-400">用户名</div>
          <div className="col-span-2">{user.username}</div>
          <div className="text-slate-500 dark:text-slate-400">注册时间</div>
          <div className="col-span-2">{user.created_at}</div>
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5"
      >
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <Mail className="w-4 h-4 text-brand-500" /> 默认收件邮箱
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
          下次发起「邮件投递」类请求时会自动带上该邮箱
        </p>
        <input
          type="email"
          className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@example.com"
        />
        <div className="flex items-center gap-3 mt-3">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-1.5 rounded-md bg-brand-500 hover:bg-brand-600 text-white flex items-center gap-1 text-sm disabled:bg-slate-400"
          >
            <Save className="w-4 h-4" /> {saving ? '保存中...' : '保存'}
          </button>
          {msg && <span className="text-sm text-emerald-600">{msg}</span>}
          {err && <span className="text-sm text-rose-600">{err}</span>}
        </div>
      </form>
    </div>
  );
}
