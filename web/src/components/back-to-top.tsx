"use client";

import { motion, useScroll, useSpring } from "framer-motion";

export default function BackToTop() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <>
      {/* Scroll progress bar — thin gold line at top of page */}
      <motion.div
        className="fixed top-0 inset-x-0 z-[60] h-[2px] origin-left bg-[#d4a853] pointer-events-none"
        style={{ scaleX }}
      />

      {/* Back-to-top floating button */}
      <motion.button
        onClick={scrollToTop}
        initial={{ opacity: 0, scale: 0.5, y: 20 }}
        whileInView={{ opacity: 1, scale: 1, y: 0 }}
        viewport={{ margin: "-200px" }}
        whileHover={{ scale: 1.1, boxShadow: "0 0 20px rgba(212,168,83,0.3)" }}
        whileTap={{ scale: 0.9 }}
        className="fixed bottom-6 right-6 z-50 w-11 h-11 rounded-full bg-[#18181b] border border-[#27272a] text-[#d4a853] flex items-center justify-center shadow-lg hover:border-[#d4a853]/40 transition-colors duration-300 cursor-pointer"
        aria-label="回到顶部"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M8 3L3 8M8 3L13 8M8 3V13"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </motion.button>
    </>
  );
}
