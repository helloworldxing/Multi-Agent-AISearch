import { ReactNode } from 'react';

type Phase =
  | 'idle' | 'planning' | 'awaiting_approval' | 'running' | 'done' | 'error'
  | 'routing' | 'chatting' | 'researching' | 'writing';

const PHASE_STYLE: Record<string, string> = {
  routing:           'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  planning:          'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  awaiting_approval: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  researching:       'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  writing:           'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  chatting:          'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
  running:           'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  done:              'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  error:             'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
};

export default function StatusBar({ phase, children }: { phase: Phase; children: ReactNode }) {
  const cls = PHASE_STYLE[phase] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
  return (
    <div className={`px-4 py-2 rounded-md text-sm mb-3 ${cls}`}>
      {children}
    </div>
  );
}
