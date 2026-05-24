const variants = {
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-red-100 text-red-700',
  info: 'bg-brand-100 text-brand-700',
  neutral: 'bg-surface-100 text-text-secondary',
};

interface StatusPillProps {
  label: string;
  variant?: keyof typeof variants;
}

export function StatusPill({ label, variant = 'neutral' }: StatusPillProps) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${variants[variant]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${variant === 'success' ? 'bg-emerald-500' : variant === 'warning' ? 'bg-amber-500' : variant === 'error' ? 'bg-red-500' : variant === 'info' ? 'bg-brand-500' : 'bg-slate-400'}`} />
      {label}
    </span>
  );
}
