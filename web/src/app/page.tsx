import Nav from "@/components/nav";
import Hero from "@/components/hero";
import PipelineGrid from "@/components/pipeline-grid";
import PhasePanels from "@/components/phase-panels";
import Footer from "@/components/footer";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <PipelineGrid />
        <PhasePanels />
      </main>
      <Footer />
    </>
  );
}
