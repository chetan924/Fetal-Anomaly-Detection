function Badge({ children, tone = 'info', className = '' }) {
  const tones = {
    info: 'bg-cyan-50 text-cyan-700',
    success: 'bg-emerald-50 text-emerald-700',
    warning: 'bg-amber-50 text-amber-700',
    danger: 'bg-rose-50 text-rose-700',
  };

  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${tones[tone]} ${className}`}>{children}</span>;
}

export default Badge;
