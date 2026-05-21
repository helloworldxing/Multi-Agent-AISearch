import { ArrowDown, ArrowUp, CheckCircle2, Plus, X, XCircle } from 'lucide-react';

interface Props {
  intent: 'research' | 'email' | 'chat';
  subqueries: string[];
  onChange: (next: string[]) => void;
  onApprove: () => void;
  onCancel: () => void;
}

const INTENT_BADGE: Record<string, { text: string; cls: string }> = {
  chat:     { text: '普通对话', cls: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' },
  research: { text: '主题研究', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
  email:    { text: '邮件投递', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
};

export default function ApprovalModal({
  intent,
  subqueries,
  onChange,
  onApprove,
  onCancel,
}: Props) {
  const badge = INTENT_BADGE[intent] || INTENT_BADGE.research;

  const update = (i: number, value: string) => {
    const next = subqueries.slice();
    next[i] = value;
    onChange(next);
  };
  const remove = (i: number) => {
    onChange(subqueries.filter((_, idx) => idx !== i));
  };
  const move = (i: number, delta: number) => {
    const target = i + delta;
    if (target < 0 || target >= subqueries.length) return;
    const next = subqueries.slice();
    [next[i], next[target]] = [next[target], next[i]];
    onChange(next);
  };
  const add = () => {
    onChange([...subqueries, '']);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold">执行步骤预览</h3>
            <span className={`px-2 py-0.5 rounded-full text-xs ${badge.cls}`}>
              {badge.text}
            </span>
          </div>
          <button
            onClick={onCancel}
            className="p-1 rounded text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            title="取消"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-5 py-3 text-sm text-slate-500 dark:text-slate-400">
          下面是 AI 拆解出的子任务，你可以修改、增删、调整顺序。确认无误后点击「确认执行」。
        </div>

        <div className="px-5 pb-4 overflow-auto flex-1">
          <div className="flex flex-col gap-2">
            {subqueries.map((q, i) => (
              <div
                key={i}
                className="flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-2"
              >
                <div className="w-7 h-7 rounded-full bg-brand-500 text-white text-xs flex items-center justify-center flex-shrink-0">
                  {i + 1}
                </div>
                <input
                  className="flex-1 px-3 py-1.5 text-sm rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:border-brand-400"
                  value={q}
                  onChange={(e) => update(i, e.target.value)}
                />
                <button
                  className="p-1.5 rounded text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-transparent"
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  title="上移"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>
                <button
                  className="p-1.5 rounded text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-transparent"
                  onClick={() => move(i, 1)}
                  disabled={i === subqueries.length - 1}
                  title="下移"
                >
                  <ArrowDown className="w-4 h-4" />
                </button>
                <button
                  className="p-1.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                  onClick={() => remove(i)}
                  title="删除"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={add}
            className="mt-3 w-full py-2 rounded-lg border border-dashed border-brand-400 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-slate-800 flex items-center justify-center gap-1 text-sm"
          >
            <Plus className="w-4 h-4" /> 添加步骤
          </button>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onCancel}
            className="px-4 py-1.5 text-sm rounded-md border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-1"
          >
            <XCircle className="w-4 h-4" /> 取消
          </button>
          <button
            onClick={onApprove}
            disabled={subqueries.length === 0}
            className="px-4 py-1.5 text-sm rounded-md bg-brand-500 hover:bg-brand-600 text-white disabled:bg-slate-400 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <CheckCircle2 className="w-4 h-4" /> 确认执行
          </button>
        </div>
      </div>
    </div>
  );
}
