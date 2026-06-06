"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Upload,
  ChartBar,
  TreeStructure,
  Article,
  CheckSquare,
  FilmStrip,
  Download,
  FileText,
  Eye,
  Code,
  Image as ImageIcon,
} from "@phosphor-icons/react";
import { getScript, type ScriptData } from "@/lib/api";

const DEFAULT_PROJECT = "青云之路";

/* ── Tab definitions ── */
const TABS = [
  { id: "ingest", label: "导入", icon: Upload },
  { id: "analyze", label: "分析", icon: ChartBar },
  { id: "plan", label: "规划", icon: TreeStructure },
  { id: "write", label: "剧本", icon: Article },
  { id: "review", label: "审核", icon: CheckSquare },
  { id: "storyboard", label: "分镜", icon: FilmStrip },
  { id: "export", label: "导出", icon: Download },
];

/* ── Syntax-highlighted YAML viewer ── */
function YamlViewer({ content }: { content: string }) {
  const highlighted = content
    .split("\n")
    .map((line) => {
      const indent = line.match(/^(\s*)/)?.[1].length ?? 0;
      const trimmed = line.trim();

      if (!trimmed || trimmed.startsWith("#"))
        return `<span style="padding-left:${
          indent * 2
        }ch"><span class="yaml-comment">${trimmed}</span></span>`;

      const colonIdx = trimmed.indexOf(":");
      if (colonIdx === -1)
        return `<span style="padding-left:${indent * 2}ch">${trimmed}</span>`;

      const key = trimmed.slice(0, colonIdx);
      const value = trimmed.slice(colonIdx + 1).trim();

      let valClass = "yaml-val";
      if (value === "true" || value === "false") valClass = "yaml-bool";
      else if (/^\d+$/.test(value)) valClass = "yaml-num";

      return `<span style="padding-left:${indent * 2}ch"><span class="yaml-key">${key}</span>: <span class="${valClass}">${value}</span></span>`;
    })
    .join("\n");

  return (
    <pre
      className="code-surface p-5 overflow-x-auto text-[13px] leading-[1.7]"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  );
}

/* ── Placeholder panel ── */
function PlaceholderPanel({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-5">
        <Icon size={28} className="text-[#71717a]" />
      </div>
      <h3 className="text-lg font-semibold text-[#f4f4f5] mb-2">{title}</h3>
      <p className="text-sm text-[#a1a1aa] max-w-[400px]">{description}</p>
      <p className="mt-4 text-[11px] font-mono text-[#71717a]">
        运行管线以填充此区域
      </p>
    </div>
  );
}

/* ── Script Editor Panel ── */
function ScriptPanel() {
  const [episode, setEpisode] = useState(1);
  const [view, setView] = useState<"yaml" | "preview">("yaml");
  const [script, setScript] = useState<ScriptData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScript = useCallback(async (ep: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getScript(DEFAULT_PROJECT, ep);
      setScript(data);
    } catch (e) {
      setError(String(e));
      setScript(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchScript(episode);
  }, [episode, fetchScript]);

  // Count scenes and elements from YAML content
  const sceneCount = script?.content
    ? (script.content.match(/^\s*- id:/gm) || []).length
    : 0;
  const elementCount = script?.content
    ? (script.content.match(/^\s*- type:/gm) || []).length
    : 0;

  return (
    <div className="flex flex-col gap-5">
      {/* Episode selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <button
            key={ep}
            onClick={() => setEpisode(ep)}
            className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all duration-200 ${
              episode === ep
                ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
            }`}
          >
            Ep {ep.toString().padStart(2, "0")}
          </button>
        ))}
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-1 p-1 bg-[#18181b] border border-[#27272a] rounded-lg w-fit">
        <button
          onClick={() => setView("yaml")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] rounded-md transition-all ${
            view === "yaml"
              ? "bg-[#09090b] text-[#d4a853] shadow-sm"
              : "text-[#71717a] hover:text-[#a1a1aa]"
          }`}
        >
          <Code size={14} /> YAML
        </button>
        <button
          onClick={() => setView("preview")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] rounded-md transition-all ${
            view === "preview"
              ? "bg-[#09090b] text-[#d4a853] shadow-sm"
              : "text-[#71717a] hover:text-[#a1a1aa]"
          }`}
        >
          <Eye size={14} /> 预览
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="card-surface p-12 flex items-center justify-center">
          <p className="text-sm text-[#71717a]">正在从API加载剧本...</p>
        </div>
      ) : error ? (
        <div className="card-surface p-12 flex flex-col items-center justify-center gap-3">
          <p className="text-sm text-[#a1a1aa]">暂无剧本数据</p>
          <p className="text-[11px] font-mono text-[#71717a]">
            运行管线以生成剧本，或检查API服务器是否正常运行。
          </p>
        </div>
      ) : view === "yaml" ? (
        <YamlViewer content={script?.content || "# 暂无剧本数据\n# 运行管线以生成剧本"} />
      ) : (
        <div className="card-surface p-8">
          <div className="max-w-[65ch] mx-auto space-y-6 text-sm leading-relaxed text-[#a1a1aa]">
            <h3 className="text-xl font-semibold text-[#f4f4f5]">
              第{episode}集: 剧本预览
            </h3>
            <div className="flex items-center gap-4 text-[11px] font-mono text-[#71717a]">
              <span>场次: {sceneCount}</span>
              <span>元素: {elementCount}</span>
              <span>路径: {script?.path || "无"}</span>
            </div>
            <p className="text-[#f4f4f5]">
              {script?.content
                ? "已从API加载剧本。切换到YAML视图查看完整语法高亮内容。"
                : "尚未生成剧本。运行「编写」阶段以生成单集剧本。"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Analysis Panel ── */
function AnalysisPanel() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <FileText size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">
            分析报告
          </h3>
        </div>
        <div className="space-y-3 text-sm text-[#a1a1aa]">
          {[
            ["叙事结构", "三幕式"],
            ["视角", "第三人称限知"],
            ["节奏评分", "84/100"],
            ["改编难度", "中等"],
            ["推荐媒介", "电视剧"],
          ].map(([label, value]) => (
            <div
              key={label}
              className="flex justify-between py-2 border-b border-[#1f1f23] last:border-0"
            >
              <span>{label}</span>
              <span className="font-mono text-[#d4a853]">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <ChartBar size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">
            角色关系网络
          </h3>
        </div>
        <div className="space-y-3 text-sm">
          {[
            { name: "林逸", role: "主角", relations: 8, arc: "上升" },
            { name: "老者", role: "导师", relations: 2, arc: "退场" },
            { name: "小翠", role: "盟友", relations: 4, arc: "出场" },
            { name: "黑衣人", role: "反派", relations: 5, arc: "发展" },
            { name: "萧剑", role: "对手", relations: 6, arc: "伏笔" },
          ].map((char) => (
            <div
              key={char.name}
              className="flex items-center justify-between py-2 border-b border-[#1f1f23] last:border-0"
            >
              <div>
                <span className="text-[#f4f4f5] font-medium">{char.name}</span>
                <span className="ml-2 text-[11px] font-mono text-[#71717a]">
                  {char.role}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-[11px] text-[#71717a]">
                  {char.relations} 个关联
                </span>
                <span
                  className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
                    char.arc === "上升" || char.arc === "发展"
                      ? "bg-[#22c55e]/10 text-[#22c55e]"
                      : char.arc === "伏笔"
                      ? "bg-[#3b82f6]/10 text-[#3b82f6]"
                      : "bg-[#71717a]/10 text-[#71717a]"
                  }`}
                >
                  {char.arc}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Export Panel ── */
function ExportPanel() {
  const items = [
    {
      label: "YAML 剧本",
      desc: "全部集数，Schema v2.0 YAML格式，含完整元数据",
      icon: Code,
      size: "~240 KB",
    },
    {
      label: "纯文本",
      desc: "标准剧本格式，兼容外部编辑工具",
      icon: FileText,
      size: "~180 KB",
    },
    {
      label: "分镜包",
      desc: "镜头列表、帧描述和视觉参考合集",
      icon: ImageIcon,
      size: "~420 KB",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Primary: YAML - spans 2 cols */}
        <div className="lg:col-span-2 card-surface p-6 flex flex-col md:flex-row gap-6 items-start">
          <div className="w-12 h-12 rounded-xl bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center shrink-0">
            <Code size={22} className="text-[#d4a853]" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-[#f4f4f5]">
              {items[0].label}
            </h4>
            <p className="text-[13px] text-[#a1a1aa] mt-1 max-w-[400px]">
              {items[0].desc}
            </p>
            <p className="text-[11px] font-mono text-[#71717a] mt-2">
              {items[0].size}
            </p>
          </div>
          <button className="px-5 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all duration-200 active:scale-[0.98] shrink-0">
            下载 YAML
          </button>
        </div>

        {/* Plain Text */}
        <div className="card-surface p-5 flex flex-col gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center">
            <FileText size={18} className="text-[#d4a853]" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[#f4f4f5]">
              {items[1].label}
            </h4>
            <p className="text-[12px] text-[#a1a1aa] mt-1">{items[1].desc}</p>
            <p className="text-[11px] font-mono text-[#71717a] mt-2">
              {items[1].size}
            </p>
          </div>
          <button className="w-full mt-auto px-4 py-2 text-[13px] font-medium rounded-lg border border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] hover:border-[#3f3f46] transition-all duration-200 active:scale-[0.98]">
            下载文本
          </button>
        </div>
      </div>

      {/* Storyboard - full width */}
      <div className="card-surface p-5 flex flex-col sm:flex-row gap-5 items-start">
        <div className="w-10 h-10 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center shrink-0">
          <ImageIcon size={18} className="text-[#d4a853]" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-[#f4f4f5]">
            {items[2].label}
          </h4>
          <p className="text-[12px] text-[#a1a1aa] mt-1 max-w-[500px]">
            {items[2].desc}
          </p>
          <p className="text-[11px] font-mono text-[#71717a] mt-2">
            {items[2].size}
          </p>
        </div>
        <button className="px-5 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all duration-200 active:scale-[0.98] shrink-0">
          下载分镜包
        </button>
      </div>
    </div>
  );
}

/* ── Main Phase Panels Component ── */
export default function PhasePanels() {
  const [activeTab, setActiveTab] = useState("write");

  const renderPanel = () => {
    switch (activeTab) {
      case "ingest":
        return (
          <PlaceholderPanel
            icon={Upload}
            title="导入与知识库"
            description="上传源小说，扫描术语，为改编管线建立知识注册表。"
          />
        );
      case "analyze":
        return <AnalysisPanel />;
      case "plan":
        return (
          <PlaceholderPanel
            icon={TreeStructure}
            title="分集规划"
            description="章节到集数的映射，含情绪曲线设计和悬念钩子生成。"
          />
        );
      case "write":
        return <ScriptPanel />;
      case "review":
        return (
          <PlaceholderPanel
            icon={CheckSquare}
            title="审核中心"
            description="多维度审核：业务逻辑评分、合规检查和参考剧本对比。"
          />
        );
      case "storyboard":
        return (
          <PlaceholderPanel
            icon={FilmStrip}
            title="分镜预览"
            description="电影级镜头规划，双轨支持：传统Film分镜和Seedance AI。"
          />
        );
      case "export":
        return <ExportPanel />;
      default:
        return null;
    }
  };

  return (
    <section id="dashboard" className="py-24 px-6">
      <div className="max-w-[1400px] mx-auto">
        <div className="mb-10">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#f4f4f5]">
            阶段详情
          </h2>
          <p className="mt-3 text-sm text-[#a1a1aa] max-w-[65ch]">
            深入每个管线阶段。编辑剧本、查看分析、管理产出。
          </p>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-0.5 mb-8 overflow-x-auto pb-2 border-b border-[#27272a]">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium whitespace-nowrap rounded-t-lg transition-all duration-200 ${
                activeTab === tab.id
                  ? "text-[#d4a853] bg-[#d4a853]/5 border-b-2 border-[#d4a853]"
                  : "text-[#71717a] hover:text-[#a1a1aa] border-b-2 border-transparent"
              }`}
            >
              <tab.icon
                size={15}
                weight={activeTab === tab.id ? "fill" : "regular"}
              />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Panel content */}
        <div key={activeTab}>{renderPanel()}</div>
      </div>
    </section>
  );
}
