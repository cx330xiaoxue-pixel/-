const PHASE_LABELS = [
  "导入", "分析", "规划", "编写", "审核", "分镜",
];

export default function Hero() {
  return (
    <section
      id="hero"
      className="relative min-h-[100dvh] flex flex-col items-center justify-center px-6 pt-24 pb-16"
    >
      {/* Ambient accent glow */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-[0.08] pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, var(--accent) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 max-w-[720px] mx-auto text-center">
        {/* Eyebrow */}
        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#d4a853] mb-6">
          AI驱动的改编管线
        </p>

        {/* Headline */}
        <h1 className="text-4xl md:text-6xl lg:text-7xl font-semibold tracking-tighter leading-[1.05] text-[#f4f4f5]">
          从小说到剧本，
          <br />
          <span className="text-[#d4a853]">AI赋能创作</span>
        </h1>

        {/* Subtext */}
        <p className="mt-6 text-base md:text-lg text-[#a1a1aa] leading-relaxed max-w-[540px] mx-auto">
          六阶段管线将原始小说转化为专业剧本，
          涵盖角色分析、场景拆解和电影级分镜设计。
        </p>

        {/* Pipeline flow strip */}
        <div className="mt-10 flex items-center justify-center gap-1 flex-wrap">
          {PHASE_LABELS.map((label, i) => (
            <span key={label} className="flex items-center gap-1">
              <span className="px-3 py-1.5 text-[12px] font-mono text-[#a1a1aa] bg-[#18181b] border border-[#27272a] rounded-md">
                {label}
              </span>
              {i < PHASE_LABELS.length - 1 && (
                <span className="w-4 h-px bg-[#3f3f46] mx-0.5" />
              )}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
