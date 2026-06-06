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
  { id: "ingest", label: "Import", icon: Upload },
  { id: "analyze", label: "Analysis", icon: ChartBar },
  { id: "plan", label: "Planning", icon: TreeStructure },
  { id: "write", label: "Script", icon: Article },
  { id: "review", label: "Review", icon: CheckSquare },
  { id: "storyboard", label: "Storyboard", icon: FilmStrip },
  { id: "export", label: "Export", icon: Download },
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
        Run the pipeline to populate this section
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
        <span className="text-sm text-[#71717a]">Episode:</span>
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
          <Eye size={14} /> Preview
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="card-surface p-12 flex items-center justify-center">
          <p className="text-sm text-[#71717a]">Loading script from API...</p>
        </div>
      ) : error ? (
        <div className="card-surface p-12 flex flex-col items-center justify-center gap-3">
          <p className="text-sm text-[#a1a1aa]">No script data available</p>
          <p className="text-[11px] font-mono text-[#71717a]">
            Run the pipeline to generate scripts, or check that the API server is running.
          </p>
        </div>
      ) : view === "yaml" ? (
        <YamlViewer content={script?.content || "# No script data yet\n# Run the pipeline to generate scripts"} />
      ) : (
        <div className="card-surface p-8">
          <div className="max-w-[65ch] mx-auto space-y-6 text-sm leading-relaxed text-[#a1a1aa]">
            <h3 className="text-xl font-semibold text-[#f4f4f5]">
              Episode {episode}: Script Preview
            </h3>
            <div className="flex items-center gap-4 text-[11px] font-mono text-[#71717a]">
              <span>Scenes: {sceneCount}</span>
              <span>Elements: {elementCount}</span>
              <span>Path: {script?.path || "N/A"}</span>
            </div>
            <p className="text-[#f4f4f5]">
              {script?.content
                ? "Script loaded from API. Switch to YAML view for full syntax-highlighted content."
                : "No script generated yet. Run the Write phase to generate episode scripts."}
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
            Analysis Report
          </h3>
        </div>
        <div className="space-y-3 text-sm text-[#a1a1aa]">
          {[
            ["Narrative Structure", "Three-Act"],
            ["POV", "Third Person Limited"],
            ["Pacing Score", "84/100"],
            ["Adaptation Difficulty", "Medium"],
            ["Recommended Medium", "TV Series"],
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
            Character Network
          </h3>
        </div>
        <div className="space-y-3 text-sm">
          {[
            { name: "林逸", role: "Hero", relations: 8, arc: "Rising" },
            { name: "老者", role: "Mentor", relations: 2, arc: "Exit" },
            { name: "小翠", role: "Ally", relations: 4, arc: "Introduction" },
            { name: "黑衣人", role: "Antagonist", relations: 5, arc: "Building" },
            { name: "萧剑", role: "Rival", relations: 6, arc: "Foreshadowed" },
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
                  {char.relations} links
                </span>
                <span
                  className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
                    char.arc === "Rising" || char.arc === "Building"
                      ? "bg-[#22c55e]/10 text-[#22c55e]"
                      : char.arc === "Foreshadowed"
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
      label: "YAML Scripts",
      desc: "All episodes in schema v2.0 YAML format with full metadata",
      icon: Code,
      size: "~240 KB",
    },
    {
      label: "Plain Text",
      desc: "Standard screenplay format for external editing tools",
      icon: FileText,
      size: "~180 KB",
    },
    {
      label: "Storyboard Package",
      desc: "Shot lists, frame descriptions, and visual reference bundle",
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
            Download YAML
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
            Download Text
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
          Download Package
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
            title="Import & Knowledge"
            description="Upload source novels, scan for terminology, and build the knowledge registry for the adaptation pipeline."
          />
        );
      case "analyze":
        return <AnalysisPanel />;
      case "plan":
        return (
          <PlaceholderPanel
            icon={TreeStructure}
            title="Episode Planning"
            description="Chapter-to-episode mapping with emotion curve design and suspense hook generation."
          />
        );
      case "write":
        return <ScriptPanel />;
      case "review":
        return (
          <PlaceholderPanel
            icon={CheckSquare}
            title="Review Center"
            description="Multi-dimension review: business logic scoring, compliance check, and reference script comparison."
          />
        );
      case "storyboard":
        return (
          <PlaceholderPanel
            icon={FilmStrip}
            title="Storyboard Preview"
            description="Cinematic shot planning with dual-track support: traditional Film Storyboard and Seedance AI."
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
            Phase Details
          </h2>
          <p className="mt-3 text-sm text-[#a1a1aa] max-w-[65ch]">
            Dive into each pipeline phase. Edit scripts, review analysis, and
            manage outputs.
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
