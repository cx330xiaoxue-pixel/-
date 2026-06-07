"use client";

import { useState, useEffect } from "react";
import { motion, type TargetAndTransition } from "framer-motion";
import { easeOutExpo } from "@/lib/motion";

const NAV_ITEMS = [
  { id: "pipeline", label: "管线" },
  { id: "dashboard", label: "仪表盘" },
  { id: "write", label: "剧本" },
  { id: "review", label: "审核" },
  { id: "export", label: "导出" },
];

const navVariants = {
  hidden: { y: -80, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.8,
      ease: easeOutExpo,
    },
  },
};

const itemVariants = {
  hidden: { y: -16, opacity: 0 },
  visible: (i: number): TargetAndTransition => ({
    y: 0,
    opacity: 1,
    transition: {
      delay: 0.25 + i * 0.06,
      duration: 0.5,
      ease: "easeOut",
    },
  }),
};

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          setScrolled(window.scrollY > 32);
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <motion.nav
      variants={navVariants}
      initial="hidden"
      animate="visible"
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
        scrolled
          ? "bg-[#09090b]/85 backdrop-blur-xl border-b border-[#1f1f23] shadow-[0_1px_0_0_rgba(212,168,83,0.05)]"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto max-w-[1400px] px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <motion.button
          onClick={() => scrollTo("hero")}
          className="flex items-center gap-2.5 text-[#f4f4f5] group cursor-pointer"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          <motion.span
            className="w-8 h-8 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/30 flex items-center justify-center"
            whileHover={{
              boxShadow: "0 0 22px rgba(212, 168, 83, 0.3)",
              borderColor: "rgba(212, 168, 83, 0.55)",
            }}
            transition={{ duration: 0.3 }}
          >
            <span className="text-[#d4a853] text-sm font-bold">N</span>
          </motion.span>
          <span className="font-semibold text-sm tracking-tight hidden sm:block group-hover:text-[#d4a853] transition-colors duration-300">
            Novel-to-Script Pro
          </span>
        </motion.button>

        {/* Nav items */}
        <div className="hidden lg:flex items-center gap-1">
          {NAV_ITEMS.map((item, i) => (
            <motion.button
              key={item.id}
              custom={i}
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              onClick={() => scrollTo(item.id)}
              whileHover={{ scale: 1.06, y: -1 }}
              whileTap={{ scale: 0.95 }}
              className="relative px-3 py-2 rounded-lg text-[13px] font-medium text-[#a1a1aa] hover:text-[#f4f4f5] hover:bg-[#18181b] transition-colors duration-200 cursor-pointer"
            >
              {item.label}
              <motion.span
                className="absolute bottom-0 left-1/2 h-[2px] bg-[#d4a853] rounded-full"
                initial={{ width: 0 }}
                whileHover={{ width: "60%", left: "20%" }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              />
            </motion.button>
          ))}
        </div>

        {/* CTA */}
        <motion.button
          custom={5}
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          onClick={() => scrollTo("pipeline")}
          whileHover={{
            scale: 1.05,
            boxShadow: "0 0 28px rgba(212, 168, 83, 0.35)",
          }}
          whileTap={{ scale: 0.94 }}
          className="px-4 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#efbf5e] transition-colors duration-200 cursor-pointer"
        >
          启动管线
        </motion.button>
      </div>
    </motion.nav>
  );
}
