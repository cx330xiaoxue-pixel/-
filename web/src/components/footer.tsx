"use client";

import { motion } from "framer-motion";
import { staggerContainer, fadeUpItem } from "@/lib/motion";

export default function Footer() {
  return (
    <motion.footer
      id="export"
      className="py-16 px-6 border-t border-[var(--border)]"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
      variants={staggerContainer}
    >
      <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand */}
        <motion.div variants={fadeUpItem} className="flex items-center gap-2.5">
          <motion.span
            className="w-7 h-7 rounded-md bg-[var(--accent)]/10 border border-[var(--accent)]/30 flex items-center justify-center"
            whileHover={{
              boxShadow: "0 0 16px rgba(212, 168, 83, 0.25)",
              borderColor: "rgba(212, 168, 83, 0.5)",
            }}
            transition={{ duration: 0.3 }}
          >
            <span className="text-[var(--accent)] text-xs font-bold">N</span>
          </motion.span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            Novel-to-Script Pro
          </span>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">
            v2.0
          </span>
        </motion.div>

        {/* Links */}
        <motion.div
          variants={fadeUpItem}
          className="flex items-center gap-6 text-[13px] text-[var(--text-muted)]"
        >
          {[
            { label: "管线", value: "6阶段" },
            { label: "Agent", value: "13个" },
            { label: "技能", value: "16个" },
            { label: "Schema", value: "v2.0" },
          ].map((stat) => (
            <motion.span
              key={stat.label}
              className="flex items-center gap-1.5"
              whileHover={{ color: "#d4a853", scale: 1.05 }}
              transition={{ duration: 0.2 }}
            >
              <span>{stat.label}:</span>
              <span className="text-[var(--text-secondary)] font-mono">
                {stat.value}
              </span>
            </motion.span>
          ))}
        </motion.div>

        {/* Copyright */}
        <motion.p
          variants={fadeUpItem}
          className="text-[12px] text-[var(--text-muted)]"
        >
          为编剧和内容创作者打造
        </motion.p>
      </div>
    </motion.footer>
  );
}
