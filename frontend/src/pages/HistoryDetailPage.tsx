import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api, HistoryDetail } from '../lib/api';
import MarkdownView from '../components/MarkdownView';

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [item, setItem] = useState<HistoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getHistory(Number(id))
      .then(setItem)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'));
  }, [id]);

  return (
    <div className="max-w-4xl mx-auto mt-6">
      <Link
        to="/history"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 dark:hover:text-brand-300 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> 返回历史列表
      </Link>

      {error && (
        <div className="text-sm text-rose-600 bg-rose-50 dark:bg-rose-900/20 px-3 py-2 rounded">
          {error}
        </div>
      )}

      {item && (
        <>
          <h2 className="text-xl font-semibold mb-1">{item.topic}</h2>
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            {item.created_at} · 意图 {item.intent}
            {item.email_to && ` · 已发往 ${item.email_to}`}
          </div>

          {item.subqueries.length > 0 && (
            <div className="mb-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
              <h3 className="text-sm font-medium mb-2">执行步骤</h3>
              <ol className="list-decimal pl-6 text-sm space-y-1">
                {item.subqueries.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ol>
            </div>
          )}

          <MarkdownView content={item.document} />
        </>
      )}
    </div>
  );
}
