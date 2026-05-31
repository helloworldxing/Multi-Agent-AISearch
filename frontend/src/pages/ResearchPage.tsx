import { useState } from 'react';
import { Send, RotateCcw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useResearch } from '../hooks/useResearch';
import ApprovalModal from '../components/ApprovalModal';
import StatusBar from '../components/StatusBar';
import SubtaskGrid from '../components/SubtaskGrid';
import MarkdownView from '../components/MarkdownView';

const INTENT_LABEL: Record<string, { text: string; cls: string }> = {
  chat:     { text: '普通对话', cls: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' },
  research: { text: '主题研究', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
  email:    { text: '邮件投递', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
};

export default function ResearchPage() {
  const { user } = useAuth();
  const { state, requestPlan, setSubqueries, approveAndRun, cancelApproval, reset } =
    useResearch();
  const [topic, setTopic] = useState('');

  const submitting =
    state.phase === 'planning' || state.phase === 'running';
  const canSubmit = topic.trim() && !submitting;
  const isIdle = state.phase === 'idle';

  const onSend = () => {
    if (!canSubmit) return;
    // 邮件投递意图所用的收件箱直接读用户面板里的默认邮箱
    requestPlan(topic.trim(), user?.email?.trim() || undefined);
  };

  return (
    <div className="max-w-4xl mx-auto mt-6 pb-32">
      <h1 className="text-2xl font-semibold text-center mb-1">AI 研究助手</h1>
      <p className="text-center text-sm text-slate-500 dark:text-slate-400 mb-6">
        任务拆解 · 用户审批 · 并行检索 · 自动汇总
      </p>

      {state.intent && !isIdle && (
        <div className="mb-3">
          <span
            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${
              INTENT_LABEL[state.intent]?.cls || INTENT_LABEL.chat.cls
            }`}
          >
            意图: {INTENT_LABEL[state.intent]?.text || state.intent}
          </span>
        </div>
      )}

      {state.statusText && (
        <StatusBar phase={state.phase as any}>{state.statusText}</StatusBar>
      )}

      <SubtaskGrid subtasks={state.subtasks} />

      {(state.phase === 'running' || state.phase === 'done') && state.output && (
        <MarkdownView content={state.output} streaming={state.phase === 'running'} />
      )}

      {state.filePath && (
        <div className="mt-3 px-3 py-2 rounded text-sm bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
          已保存至: {state.filePath}
        </div>
      )}

      {state.emailSent && (
        <div className="mt-2 px-3 py-2 rounded text-sm bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300">
          邮件投递: {state.emailSent}
        </div>
      )}

      {state.errorMessage && state.phase === 'error' && (
        <div className="mt-3 px-3 py-2 rounded text-sm bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300">
          {state.errorMessage}
        </div>
      )}

      {/* 贴底输入条 */}
      <div className="fixed inset-x-0 bottom-0 z-20 bg-gradient-to-t from-slate-50 dark:from-slate-900 from-60% to-transparent pt-6 pb-4 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-2xl p-2 shadow-lg">
            <input
              className="flex-1 px-3 py-2 bg-transparent outline-none text-[15px]"
              placeholder="例如：你好 / 2025 大模型推理优化最新进展 / 调研新能源电池并发到我邮箱"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSend()}
              disabled={submitting}
            />
            {!isIdle && (
              <button
                onClick={reset}
                className="px-3 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                title="清空"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onSend}
              disabled={!canSubmit}
              className="px-5 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white flex items-center gap-1 disabled:bg-slate-400 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" /> 发送
            </button>
          </div>
        </div>
      </div>

      {state.phase === 'awaiting_approval' && (state.intent === 'research' || state.intent === 'email') && (
        <ApprovalModal
          intent={state.intent}
          subqueries={state.subqueries}
          onChange={setSubqueries}
          onApprove={approveAndRun}
          onCancel={cancelApproval}
        />
      )}
    </div>
  );
}
