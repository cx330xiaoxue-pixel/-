"use client";

import { motion } from "framer-motion";
import { easeOutExpo } from "@/lib/motion";

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { y: 30, opacity: 0, filter: "blur(4px)" },
  visible: {
    y: 0,
    opacity: 1,
    filter: "blur(0px)",
    transition: {
      duration: 0.7,
      ease: easeOutExpo,
    },
  },
};

export default function NotFound() {
  return (
    <motion.div
      className="min-h-[100dvh] flex flex-col items-center justify-center px-6 text-center"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1
        variants={itemVariants}
        className="text-6xl md:text-8xl font-bold text-[#27272a] mb-4"
      >
        404
      </motion.h1>
      <motion.h2
        variants={itemVariants}
        className="text-xl md:text-2xl font-semibold text-[#f4f4f5] mb-3"
      >
        页面未找到
      </motion.h2>
      <motion.p
        variants={itemVariants}
        className="text-sm text-[#a1a1aa] max-w-[400px] mb-8"
      >
        您访问的页面不存在或已被移除。请检查链接是否正确。
      </motion.p>
      <motion.a
        variants={itemVariants}
        href="/"
        whileHover={{
          scale: 1.05,
          boxShadow: "0 0 24px rgba(212, 168, 83, 0.35)",
        }}
        whileTap={{ scale: 0.95 }}
        className="px-5 py-2.5 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-colors duration-200"
      >
        返回首页
      </motion.a>
    </motion.div>
  );
}
