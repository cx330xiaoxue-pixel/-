"use client";

import { useState, useEffect } from "react";

const NAV_ITEMS = [
  { id: "pipeline", label: "Pipeline" },
  { id: "dashboard", label: "Dashboard" },
  { id: "write", label: "Script" },
  { id: "review", label: "Review" },
  { id: "export", label: "Export" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  // Simple scroll detection for backdrop - debounced via rAF
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
    <nav
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#09090b]/80 backdrop-blur-xl border-b border-[#1f1f23]"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto max-w-[1400px] px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <button
          onClick={() => scrollTo("hero")}
          className="flex items-center gap-2.5 text-[#f4f4f5] hover:text-[#d4a853] transition-colors"
        >
          <span className="w-8 h-8 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/30 flex items-center justify-center">
            <span className="text-[#d4a853] text-sm font-bold">N</span>
          </span>
          <span className="font-semibold text-sm tracking-tight hidden sm:block">
            Novel-to-Script Pro
          </span>
        </button>

        {/* Nav items */}
        <div className="hidden lg:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => scrollTo(item.id)}
              className="px-3 py-2 rounded-lg text-[13px] font-medium text-[#a1a1aa] hover:text-[#f4f4f5] hover:bg-[#18181b] transition-all duration-200"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={() => scrollTo("pipeline")}
          className="px-4 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all duration-200 active:scale-[0.98]"
        >
          Start Pipeline
        </button>
      </div>
    </nav>
  );
}
