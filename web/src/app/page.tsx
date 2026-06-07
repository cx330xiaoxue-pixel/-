"use client";

import { useState } from "react";
import Nav from "@/components/nav";
import Hero from "@/components/hero";
import PipelineGrid from "@/components/pipeline-grid";
import PhasePanels from "@/components/phase-panels";
import Footer from "@/components/footer";
import BackToTop from "@/components/back-to-top";

export default function Home() {
  const [projectName, setProjectName] = useState("测试项目");

  return (
    <>
      <Nav />
      <main>
        <Hero />
        <PipelineGrid projectName={projectName} onProjectChange={setProjectName} />
        <PhasePanels projectName={projectName} />
      </main>
      <Footer />
      <BackToTop />
    </>
  );
}
