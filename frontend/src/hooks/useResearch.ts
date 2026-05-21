import { useCallback, useRef, useState } from 'react';
import { api, getToken, PlanResp } from '../lib/api';

export type Phase =
  | 'idle'
  | 'planning'
  | 'awaiting_approval'
  | 'running'
  | 'done'
  | 'error';

export interface SubtaskState {
  idx: number;
  subquery: string;
  status: 'running' | 'done' | 'empty';
  docs?: number;
  indexed_chunks?: number;
  chunks?: number;
}

export interface StreamState {
  phase: Phase;
  intent: 'chat' | 'research' | 'email' | null;
  statusText: string;
  subqueries: string[];          // 审批阶段可编辑、执行阶段为已确认值
  subtasks: SubtaskState[];
  output: string;                // 流式累积的最终回答 / 报告
  filePath: string | null;
  emailSent: string | null;
  historyId: number | null;
  errorMessage: string | null;
}

const initialState: StreamState = {
  phase: 'idle',
  intent: null,
  statusText: '',
  subqueries: [],
  subtasks: [],
  output: '',
  filePath: null,
  emailSent: null,
  historyId: null,
  errorMessage: null,
};

export function useResearch() {
  const [state, setState] = useState<StreamState>(initialState);
  const esRef = useRef<EventSource | null>(null);
  const topicRef = useRef<string>('');
  const emailRef = useRef<string>('');

  const reset = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setState(initialState);
  }, []);

  const cancelApproval = useCallback(() => {
    setState((s) =>
      s.phase === 'awaiting_approval' ? { ...initialState } : s,
    );
  }, []);

  /** 第一阶段：拉取 plan，由前端展示给用户审批 */
  const requestPlan = useCallback(async (topic: string, email?: string) => {
    topicRef.current = topic;
    emailRef.current = email || '';
    setState({
      ...initialState,
      phase: 'planning',
      statusText: '正在判断意图与生成步骤...',
    });
    let plan: PlanResp;
    try {
      plan = await api.plan(topic, email);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '生成步骤失败';
      setState({ ...initialState, phase: 'error', errorMessage: msg });
      return;
    }
    if (plan.intent === 'chat') {
      // chat 不走审批，直接执行
      setState((s) => ({
        ...s,
        intent: 'chat',
        subqueries: [],
        phase: 'running',
        statusText: '正在回答...',
      }));
      runStream({ intent: 'chat', subqueries: [] });
      return;
    }
    setState((s) => ({
      ...s,
      intent: plan.intent,
      subqueries: plan.subqueries,
      phase: 'awaiting_approval',
      statusText: '请确认执行步骤',
    }));
  }, []);

  /** 编辑步骤（审批阶段调用） */
  const setSubqueries = useCallback((next: string[]) => {
    setState((s) => ({ ...s, subqueries: next }));
  }, []);

  /** 第二阶段：用户确认后执行 */
  const approveAndRun = useCallback(() => {
    setState((s) => {
      const cleaned = s.subqueries.map((q) => q.trim()).filter(Boolean);
      if (cleaned.length === 0) {
        return { ...s, phase: 'error', errorMessage: '请至少保留一个步骤再执行' };
      }
      const next: StreamState = {
        ...s,
        subqueries: cleaned,
        phase: 'running',
        statusText: '执行中...',
        subtasks: cleaned.map((q, i) => ({ idx: i, subquery: q, status: 'running' })),
      };
      // setState 后再触发流式
      queueMicrotask(() => runStream({ intent: s.intent || 'research', subqueries: cleaned }));
      return next;
    });
  }, []);

  function runStream(opts: { intent: string; subqueries: string[] }) {
    const token = getToken();
    if (!token) {
      setState((s) => ({ ...s, phase: 'error', errorMessage: '未登录' }));
      return;
    }
    const params = new URLSearchParams({
      topic: topicRef.current,
      intent: opts.intent,
      token,
    });
    if (emailRef.current) params.set('email', emailRef.current);
    if (opts.subqueries.length) {
      params.set('subqueries', JSON.stringify(opts.subqueries));
    }
    const es = new EventSource(`/api/research/stream?${params.toString()}`);
    esRef.current = es;

    es.addEventListener('intent', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({ ...s, intent: data.intent }));
    });
    es.addEventListener('status', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({ ...s, statusText: data.message }));
    });
    es.addEventListener('plan_done', (e) => {
      // 兜底兼容：当后端实际走了原始 workflow（理论上 execution workflow 不会触发）
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({
        ...s,
        subqueries: data.subqueries,
        subtasks: data.subqueries.map((q: string, i: number) => ({
          idx: i,
          subquery: q,
          status: 'running' as const,
        })),
      }));
    });
    es.addEventListener('subtask_done', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({
        ...s,
        subtasks: s.subtasks.map((t) =>
          t.idx === data.idx
            ? {
                ...t,
                status: data.docs === 0 || data.chunks === 0 ? 'empty' : 'done',
                docs: data.docs,
                indexed_chunks: data.indexed_chunks,
                chunks: data.chunks,
              }
            : t,
        ),
      }));
    });
    es.addEventListener('token', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({ ...s, output: s.output + data.content }));
    });
    es.addEventListener('done', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({
        ...s,
        phase: 'done',
        statusText: data.message || '完成',
        filePath: data.file || null,
        historyId: data.history_id ?? null,
      }));
      es.close();
      esRef.current = null;
    });
    es.addEventListener('email_sent', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setState((s) => ({ ...s, emailSent: data.to || data.message }));
    });
    es.addEventListener('error', (e) => {
      const ev = e as MessageEvent;
      if (ev?.data) {
        try {
          const data = JSON.parse(ev.data);
          setState((s) => ({ ...s, phase: 'error', errorMessage: data.message }));
        } catch { /* ignore */ }
      }
    });
    es.onerror = () => {
      setState((s) => {
        if (s.phase === 'done' || s.phase === 'error') return s;
        return { ...s, phase: 'error', errorMessage: '连接中断或已结束' };
      });
      es.close();
      esRef.current = null;
    };
  }

  return {
    state,
    reset,
    requestPlan,
    setSubqueries,
    approveAndRun,
    cancelApproval,
  };
}
