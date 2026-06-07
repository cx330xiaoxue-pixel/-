"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Cover from "@/components/cover";
import Nav from "@/components/nav";
import Hero from "@/components/hero";
import PipelineGrid from "@/components/pipeline-grid";
import PhasePanels from "@/components/phase-panels";
import Footer from "@/components/footer";
import BackToTop from "@/components/back-to-top";
import { easeOutExpo } from "@/lib/motion";

// ── Animation variants ──

const coverExitVariants = {
  exit: {
    opacity: 0,
    scale: 0.96,
    filter: "blur(16px)",
    transition: {
      duration: 0.7,
      ease: [0.5, 0, 0.75, 1] as [number, number, number, number],
    },
  },
};

const mainEnterVariants = {
  hidden: { opacity: 0, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    filter: "blur(0px)",
    transition: {
      duration: 0.8,
      ease: easeOutExpo,
    },
  },
};

// ── Page ──

export default function Home() {
  const [phase, setPhase] = useState<"cover" | "app">("cover");
  const [projectName, setProjectName] = useState("测试项目");

  // ── Browser history integration ──
  const handleEnter = useCallback(() => {
    // Push state so back button returns to cover
    if (typeof window !== "undefined") {
      window.history.pushState({ phase: "app" }, "", window.location.pathname);
    }
    setPhase("app");
  }, []);

  // Listen for popstate (browser back button)
  useEffect(() => {
    const onPopState = (e: PopStateEvent) => {
      if (e.state?.phase === "app") {
        // User navigated forward to app state
        setPhase("app");
      } else {
        // User navigated back — show cover
        setPhase("cover");
      }
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return (
    <AnimatePresence mode="wait">
      {phase === "cover" ? (
        <motion.div
          key="cover-wrapper"
          exit="exit"
          variants={coverExitVariants}
        >
          <Cover onEnter={handleEnter} />
        </motion.div>
      ) : (
        <motion.div
          key="main-app"
          variants={mainEnterVariants}
          initial="hidden"
          animate="visible"
        >
          <Nav />
          <main>
            <Hero />
            <PipelineGrid
              projectName={projectName}
              onProjectChange={setProjectName}
            />
            <PhasePanels projectName={projectName} />
          </main>
          <Footer />
          <BackToTop />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
