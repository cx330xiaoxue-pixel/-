export default function Footer() {
  return (
    <footer id="export" className="py-16 px-6 border-t border-[var(--border)]">
      <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <span className="w-7 h-7 rounded-md bg-[var(--accent)]/10 border border-[var(--accent)]/30 flex items-center justify-center">
            <span className="text-[var(--accent)] text-xs font-bold">N</span>
          </span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            Novel-to-Script Pro
          </span>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">
            v2.0
          </span>
        </div>

        {/* Links */}
        <div className="flex items-center gap-6 text-[13px] text-[var(--text-muted)]">
          <span>管线: 6阶段</span>
          <span>Agent: 13个</span>
          <span>技能: 16个</span>
          <span>Schema: v2.0</span>
        </div>

        {/* Copyright */}
        <p className="text-[12px] text-[var(--text-muted)]">
          为编剧和内容创作者打造
        </p>
      </div>
    </footer>
  );
}
