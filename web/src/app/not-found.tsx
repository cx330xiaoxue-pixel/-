export default function NotFound() {
  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center px-6 text-center">
      <h1 className="text-6xl md:text-8xl font-bold text-[#27272a] mb-4">
        404
      </h1>
      <h2 className="text-xl md:text-2xl font-semibold text-[#f4f4f5] mb-3">
        页面未找到
      </h2>
      <p className="text-sm text-[#a1a1aa] max-w-[400px] mb-8">
        您访问的页面不存在或已被移除。请检查链接是否正确。
      </p>
      <a
        href="/"
        className="px-5 py-2.5 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all duration-200"
      >
        返回首页
      </a>
    </div>
  );
}
