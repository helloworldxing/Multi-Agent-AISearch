import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, MessageSquare, FileText, Mail } from 'lucide-react';
import { api, HistoryItem } from '../lib/api';

const ICONS: Record<string, JSX.Element> = {
  chat: <MessageSquare className="w-4 h-4 text-indigo-500" />,
  research: <FileText className="w-4 h-4 text-emerald-500" />,
  email: <Mail className="w-4 h-4 text-amber-500" />,
};

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.listHistory()
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'));
  };
  useEffect(load, []);

  const onDelete = async (id: number) => {
    if (!confirm('确认删除这条记录？')) return;
    try {
      await api.deleteHistory(id);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  return (
    <div className="max-w-4xl mx-auto mt-8">
      <h2 className="text-xl font-semibold mb-1">历史记录</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
        最近 200 条研究 / 对话记录
      </p>

      {error && (
        <div className="text-sm text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 px-3 py-2 rounded mb-3">
          {error}
        </div>
      )}

      {items === null && (
        <div className="text-sm text-slate-500">加载中...</div>
      )}

      {items?.length === 0 && (
        <div className="text-sm text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-800 border border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center">
          暂无记录，去发起一次研究吧。
        </div>
      )}

      <div className="flex flex-col gap-2">
        {items?.map((it) => (
          <div
            key={it.id}
            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4 flex items-start gap-3 hover:shadow-sm transition-shadow"
          >
            <div className="mt-1">{ICONS[it.intent] || ICONS.chat}</div>
            <Link to={`/history/${it.id}`} className="flex-1 min-w-0">
              <div className="font-medium truncate">{it.topic}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {it.created_at} · {it.intent}
                {it.subqueries.length > 0 && ` · ${it.subqueries.length} 个子任务`}
                {it.email_to && ` · 已发往 ${it.email_to}`}
              </div>
            </Link>
            <button
              onClick={() => onDelete(it.id)}
              className="p-1.5 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/30"
              title="删除"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
