"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import { easeOutExpo } from "@/lib/motion";

// ── Variants ──

const containerVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.2,
    },
  },
};

const itemVariants: Variants = {
  hidden: { y: 40, opacity: 0, filter: "blur(6px)" },
  visible: {
    y: 0,
    opacity: 1,
    filter: "blur(0px)",
    transition: { duration: 0.75, ease: easeOutExpo },
  },
};

const posterVariants: Variants = {
  hidden: { scale: 0.9, opacity: 0, filter: "blur(10px)" },
  visible: {
    scale: 1,
    opacity: 1,
    filter: "blur(0px)",
    transition: { duration: 0.95, ease: easeOutExpo },
  },
};

// ── Floating particles config ──

const PARTICLE_COUNT = 20;

function generateParticles() {
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 2 + 1,
    duration: Math.random() * 6 + 4,
    delay: Math.random() * 4,
    opacity: Math.random() * 0.3 + 0.1,
  }));
}

// ── Props ──

interface CoverProps {
  onEnter: () => void;
}

// ── Component ──

export default function Cover({ onEnter }: CoverProps) {
  const [isExiting, setIsExiting] = useState(false);
  const [hovered, setHovered] = useState(false);
  const particles = useRef(generateParticles());
  const prefersReduced = useReducedMotion();

  // Lock body scroll while cover is mounted
  useEffect(() => {
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, []);

  // Keyboard: Enter or Space to start
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (!isExiting) handleEnter();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isExiting]);

  // Mouse parallax for poster tilt
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const tiltX = useSpring(
    useTransform(mouseX, [-1, 1], prefersReduced ? [0, 0] : [-4, 4]),
    { stiffness: 35, damping: 30 },
  );
  const tiltY = useSpring(
    useTransform(mouseY, [-1, 1], prefersReduced ? [0, 0] : [-4, 4]),
    { stiffness: 35, damping: 30 },
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
      mouseX.set(x);
      mouseY.set(y);
    },
    [mouseX, mouseY],
  );

  const handleEnter = useCallback(() => {
    if (isExiting) return;
    setIsExiting(true);
    // Brief delay for button ripple feedback before notifying parent
    setTimeout(() => onEnter(), 600);
  }, [isExiting, onEnter]);

  return (
    <motion.section
      aria-label="封面页 — Novel-to-Script Pro"
      role="banner"
      onMouseMove={handleMouseMove}
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#09090b] overflow-hidden select-none"
    >
      {/* ── Background layers ── */}

      {/* Primary ambient glow */}
      <motion.div
        aria-hidden="true"
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(212,168,83,0.10) 0%, rgba(212,168,83,0.03) 35%, transparent 70%)",
        }}
        animate={
          prefersReduced
            ? {}
            : { scale: [1, 1.06, 1], opacity: [0.5, 1, 0.5] }
        }
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Secondary blue glow */}
      <motion.div
        aria-hidden="true"
        className="absolute top-1/4 right-1/4 w-[400px] h-[400px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 70%)",
        }}
        animate={
          prefersReduced
            ? {}
            : { scale: [0.85, 1.1, 0.85], opacity: [0.2, 0.6, 0.2] }
        }
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Floating dust particles */}
      {!prefersReduced &&
        particles.current.map((p) => (
          <motion.div
            key={p.id}
            aria-hidden="true"
            className="absolute rounded-full bg-[#d4a853] pointer-events-none"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
            }}
            animate={{
              y: [-20, 20, -20],
              opacity: [p.opacity, p.opacity * 2, p.opacity],
              scale: [1, 1.5, 1],
            }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}

      {/* Grain texture */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none opacity-[0.022]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E\")",
        }}
      />

      {/* Vignette */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 40%, rgba(9,9,11,0.85) 100%)",
        }}
      />

      {/* ── Content ── */}

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex flex-col items-center gap-7 px-6 max-w-[780px] mx-auto text-center"
      >
        {/* ── Cover Poster ── */}
        <motion.div
          variants={posterVariants}
          style={{ rotateX: tiltY, rotateY: tiltX }}
          whileHover={
            prefersReduced
              ? {}
              : { scale: 1.03, transition: { duration: 0.3 } }
          }
          className="relative w-[180px] h-[256px] md:w-[220px] md:h-[312px] rounded-xl overflow-hidden border border-[#27272a] shadow-[0_32px_80px_rgba(212,168,83,0.10),0_8px_24px_rgba(0,0,0,0.5)]"
          aria-label="封面海报"
        >
          {/* Poster background */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#1c1c22] via-[#14141a] to-[#0e0e12] flex flex-col items-center justify-center gap-4 p-6">
            {/* Gold film strip borders */}
            <motion.div
              className="absolute top-0 left-0 right-0 h-[3px] bg-[#d4a853]/35"
              animate={
                prefersReduced
                  ? {}
                  : { opacity: [0.35, 0.7, 0.35] }
              }
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute bottom-0 left-0 right-0 h-[3px] bg-[#d4a853]/35"
              animate={
                prefersReduced
                  ? {}
                  : { opacity: [0.35, 0.7, 0.35] }
              }
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 1.5,
              }}
            />

            {/* Light sweep effect over poster */}
            {!prefersReduced && (
              <motion.div
                aria-hidden="true"
                className="absolute inset-0 pointer-events-none"
                animate={{
                  background: [
                    "linear-gradient(105deg, transparent 40%, rgba(212,168,83,0.06) 45%, rgba(212,168,83,0.10) 50%, rgba(212,168,83,0.06) 55%, transparent 60%)",
                    "linear-gradient(105deg, transparent 40%, rgba(212,168,83,0.06) 45%, rgba(212,168,83,0.10) 50%, rgba(212,168,83,0.06) 55%, transparent 60%)",
                  ],
                  x: ["-100%", "200%"],
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: "easeInOut",
                  repeatDelay: 2,
                }}
              />
            )}

            {/* Center icon — pulsing glow */}
            <motion.div
              className="relative z-10 w-16 h-16 rounded-2xl bg-[#d4a853]/10 border border-[#d4a853]/25 flex items-center justify-center"
              animate={
                prefersReduced
                  ? {}
                  : {
                      boxShadow: [
                        "0 0 0px rgba(212,168,83,0)",
                        "0 0 28px rgba(212,168,83,0.12)",
                        "0 0 0px rgba(212,168,83,0)",
                      ],
                    }
              }
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            >
              <span className="text-3xl font-bold text-[#d4a853]">N</span>
            </motion.div>

            {/* Poster text */}
            <div className="relative z-10 text-center">
              <p className="text-[10px] font-mono tracking-[0.2em] text-[#d4a853]/65 mb-1">
                NOVEL TO SCRIPT
              </p>
              <p className="text-[8px] font-mono text-[#71717a] tracking-widest">
                AI-DRIVEN ADAPTATION
              </p>
            </div>

            {/* Film sprocket holes (decorative) */}
            <div
              aria-hidden="true"
              className="absolute left-3 top-4 bottom-4 flex flex-col justify-between"
            >
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={`l-${i}`} className="w-2 h-2 rounded-full bg-[#27272a]" />
              ))}
            </div>
            <div
              aria-hidden="true"
              className="absolute right-3 top-4 bottom-4 flex flex-col justify-between"
            >
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={`r-${i}`} className="w-2 h-2 rounded-full bg-[#27272a]" />
              ))}
            </div>
          </div>
        </motion.div>

        {/* ── Eyebrow ── */}
        <motion.p
          variants={itemVariants}
          className="text-[11px] font-mono tracking-[0.18em] text-[#d4a853]"
        >
          小说 → 剧本 → 分镜 · 全流程 AI 改编系统
        </motion.p>

        {/* ── Main heading ── */}
        <motion.div variants={itemVariants}>
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-semibold tracking-tighter leading-[1.08] text-[#f4f4f5]">
            Novel-to-Script
            <br />
            <span className="text-[#d4a853] relative inline-block">
              Pro
              <motion.span
                className="absolute -bottom-2 left-0 h-[2px] bg-[#d4a853]/50 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: "100%" }}
                transition={{ delay: 1.0, duration: 0.7, ease: "easeOut" }}
              />
            </span>
          </h1>
        </motion.div>

        {/* ── Subtitle ── */}
        <motion.p
          variants={itemVariants}
          className="text-base md:text-lg text-[#a1a1aa] leading-relaxed max-w-[520px]"
        >
          将原创小说转化为专业影视剧本
          <br />
          <span className="text-[#71717a]">
            智能分析 · 角色挖掘 · 场景拆解 · 电影级分镜
          </span>
        </motion.p>

        {/* ── Feature chips ── */}
        <motion.div
          variants={itemVariants}
          className="flex items-center gap-2 flex-wrap justify-center"
        >
          {["6阶段管线", "13个Agent", "双轨分镜", "YAML/TXT 导出"].map(
            (label, i) => (
              <motion.span
                key={label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 + i * 0.08, duration: 0.35 }}
                className="px-3 py-1.5 text-[12px] font-mono text-[#a1a1aa] bg-[#18181b] border border-[#27272a] rounded-full"
              >
                {label}
              </motion.span>
            ),
          )}
        </motion.div>

        {/* ── CTA Button ── */}
        <motion.div variants={itemVariants}>
          <motion.button
            onClick={handleEnter}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            disabled={isExiting}
            whileHover={
              isExiting ? {} : { scale: 1.05, boxShadow: "0 0 36px rgba(212,168,83,0.38)" }
            }
            whileTap={isExiting ? {} : { scale: 0.94 }}
            aria-label="开始体验 — 进入 AI 剧本改编工作台"
            className={`relative inline-flex items-center gap-3 px-8 py-3.5 text-[15px] font-semibold rounded-xl transition-all duration-200 cursor-pointer overflow-hidden ${
              isExiting
                ? "bg-[#d4a853]/40 text-[#d4a853]/50 cursor-wait"
                : "bg-[#d4a853] text-[#09090b] hover:bg-[#efbf5e]"
            }`}
          >
            <span className="relative z-10 flex items-center gap-2">
              {isExiting ? "进入中..." : "开始体验"}
              {!isExiting && (
                <motion.svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  className="relative z-10"
                  animate={{ x: hovered ? 3 : 0 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <path
                    d="M3 8H13M13 8L9 4M13 8L9 12"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </motion.svg>
              )}
              {isExiting && (
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                  className="inline-block w-4 h-4 border-2 border-[#d4a853]/30 border-t-[#d4a853] rounded-full"
                />
              )}
            </span>
          </motion.button>
        </motion.div>

        {/* ── Hint ── */}
        <motion.p
          variants={itemVariants}
          className="text-[11px] text-[#52525b]"
        >
          按 Enter 或点击 · AI 驱动的剧本改编工作台
        </motion.p>
      </motion.div>

      {/* ── Bottom accent line ── */}
      <motion.div
        aria-hidden="true"
        className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#d4a853]/25 to-transparent"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: 1.2, duration: 0.7, ease: "easeOut" }}
      />
    </motion.section>
  );
}
