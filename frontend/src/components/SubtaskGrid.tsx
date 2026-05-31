import { CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import type { SubtaskState } from '../hooks/useResearch';

export default function SubtaskGrid({ subtasks }: { subtasks: SubtaskState[] }) {
  const total = subtasks.length;
  const finished = subtasks.filter((t) => t.status !== 'running').length;
  const pct = total > 0 ? (100 * finished) / total : 0;

  if (total === 0) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm text-slate-500 dark:text-slate-400">
          执行中（{total} 个并行子任务）
        </h3>
        <span className="text-xs text-brand-600 dark:text-brand-400 font-medium">
          {finished} / {total}
        </span>
      </div>
      <div className="h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mb-3">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-brand-300 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {subtasks.map((t) => (
          <div
            key={t.idx}
            className={[
              'p-3 rounded-lg border-l-4 border-l-slate-300 bg-white dark:bg-slate-800',
              'border border-slate-200 dark:border-slate-700 text-sm',
              t.status === 'running' ? 'border-l-amber-400 bg-amber-50/40 dark:bg-amber-900/10' : '',
              t.status === 'done'    ? 'border-l-emerald-500 bg-emerald-50/40 dark:bg-emerald-900/10' : '',
              t.status === 'empty'   ? 'border-l-rose-400 bg-rose-50/30 dark:bg-rose-900/10' : '',
            ].join(' ')}
          >
            <div className="font-medium leading-snug mb-1">
              [{t.idx + 1}] {t.subquery}
            </div>
            <div className="text-xs flex items-center gap-1.5">
              {t.status === 'running' && (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500" />
                  <span className="text-amber-600 dark:text-amber-400">检索中...</span>
                </>
              )}
              {t.status === 'done' && (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-emerald-600 dark:text-emerald-400">
                    {t.docs} 篇文档 → 索引 {t.indexed_chunks} 块 → 精排 {t.chunks} 块
                  </span>
                </>
              )}
              {t.status === 'empty' && (
                <>
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                  <span className="text-rose-600 dark:text-rose-400">未检索到有效证据</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
