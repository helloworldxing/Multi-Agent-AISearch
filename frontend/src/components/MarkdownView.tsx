import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  streaming?: boolean;
}

export default function MarkdownView({ content, streaming }: Props) {
  if (!content) return null;
  return (
    <div
      className={[
        'prose-output bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700',
        'rounded-lg p-5 text-[15px] leading-relaxed break-words',
        streaming ? 'cursor-blink' : '',
      ].join(' ')}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
