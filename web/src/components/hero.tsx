"use client";

import { useRef, useCallback } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useMotionValue,
  useSpring,
  type Variants,
  type TargetAndTransition,
} from "framer-motion";
import { easeOutExpo } from "@/lib/motion";

const PHASE_LABELS = [
  "导入",
  "分析",
  "规划",
  "编写",
  "审核",
  "分镜",
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { y: 40, opacity: 0, filter: "blur(6px)" },
  visible: {
    y: 0,
    opacity: 1,
    filter: "blur(0px)",
    transition: {
      duration: 0.85,
      ease: easeOutExpo,
    },
  },
};

const stripVariants: Variants = {
  hidden: { opacity: 0, x: -16, scale: 0.95 },
  visible: (i: number): TargetAndTransition => ({
    opacity: 1,
    x: 0,
    scale: 1,
    transition: {
      delay: 0.7 + i * 0.08,
      duration: 0.5,
      ease: "easeOut",
    },
  }),
};

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"],
  });

  const sectionOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const sectionScale = useTransform(scrollYProgress, [0, 0.8], [1, 0.93]);
  const sectionY = useTransform(scrollYProgress, [0, 0.8], [0, 50]);

  // Mouse parallax for ambient glow
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const glowX = useSpring(useTransform(mouseX, [-1, 1], [-40, 40]), {
    stiffness: 40,
    damping: 35,
  });
  const glowY = useSpring(useTransform(mouseY, [-1, 1], [-40, 40]), {
    stiffness: 40,
    damping: 35,
  });

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

  return (
    <motion.section
      ref={sectionRef}
      id="hero"
      style={{ opacity: sectionOpacity, scale: sectionScale, y: sectionY }}
      onMouseMove={handleMouseMove}
      className="relative min-h-[100dvh] flex flex-col items-center justify-center px-6 pt-24 pb-16"
    >
      {/* Ambient accent glow with mouse parallax */}
      <motion.div
        className="absolute top-1/3 left-1/2 w-[700px] h-[700px] rounded-full pointer-events-none"
        style={{
          x: glowX,
          y: glowY,
          background:
            "radial-gradient(circle, var(--accent) 0%, transparent 70%)",
        }}
        animate={{
          opacity: [0.04, 0.09, 0.04],
          scale: [1, 1.06, 1],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 max-w-[820px] mx-auto text-center"
      >
        {/* Eyebrow */}
        <motion.p
          variants={itemVariants}
          className="text-[11px] font-mono tracking-[0.15em] text-[#d4a853] mb-6"
        >
          AI驱动的改编管线
        </motion.p>

        {/* Headline */}
        <motion.h1
          variants={itemVariants}
          className="text-4xl md:text-6xl lg:text-7xl font-semibold tracking-tighter leading-[1.05] text-[#f4f4f5]"
        >
          从小说到剧本，
          <br />
          <span className="text-[#d4a853] relative inline-block">
            AI赋能创作
            <motion.span
              className="absolute -bottom-2 left-0 h-[2px] bg-[#d4a853]/50 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: "100%" }}
              transition={{ delay: 1.1, duration: 0.8, ease: "easeOut" }}
            />
          </span>
        </motion.h1>

        {/* Subtext */}
        <motion.p
          variants={itemVariants}
          className="mt-7 text-base md:text-lg text-[#a1a1aa] leading-relaxed max-w-[580px] mx-auto"
        >
          六阶段管线将原始小说转化为专业剧本，涵盖角色分析、场景拆解和电影级分镜设计。
        </motion.p>

        {/* Pipeline flow strip */}
        <motion.div
          variants={itemVariants}
          className="mt-10 flex items-center justify-center gap-1 flex-wrap"
        >
          {PHASE_LABELS.map((label, i) => (
            <motion.span
              key={label}
              custom={i}
              variants={stripVariants}
              initial="hidden"
              animate="visible"
              className="flex items-center gap-1"
            >
              <motion.span
                whileHover={{
                  scale: 1.08,
                  borderColor: "rgba(212, 168, 83, 0.5)",
                  backgroundColor: "rgba(212, 168, 83, 0.07)",
                  color: "#d4a853",
                }}
                className="px-3 py-1.5 text-[12px] font-mono text-[#a1a1aa] bg-[#18181b] border border-[#27272a] rounded-md select-none transition-colors duration-200"
              >
                {label}
              </motion.span>
              {i < PHASE_LABELS.length - 1 && (
                <motion.span
                  className="w-5 h-px bg-[#3f3f46] mx-0.5"
                  initial={{ scaleX: 0, opacity: 0 }}
                  animate={{ scaleX: 1, opacity: 1 }}
                  transition={{ delay: 1.2 + i * 0.08, duration: 0.3 }}
                />
              )}
            </motion.span>
          ))}
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.6, duration: 0.8 }}
      >
        <motion.div
          className="w-5 h-8 rounded-full border border-[#3f3f46] flex items-start justify-center pt-1.5"
          animate={{ y: [0, 7, 0] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        >
          <motion.div className="w-1 h-1.5 rounded-full bg-[#d4a853]/60" />
        </motion.div>
      </motion.div>
    </motion.section>
  );
}
