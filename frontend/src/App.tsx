import { useEffect, useState } from "react";
import { analyzePaper, getPapers } from "./api";
import type { AnalyzeResponse, Paper } from "./types";
import { Sidebar } from "./components/Sidebar";
import { PaperCard } from "./components/PaperCard";
import { GapTabs } from "./components/GapTabs";
import { UploadBar } from "./components/UploadBar";
import { BrandLogo } from "./components/BrandLogo";

export default function App() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPapers()
      .then((data) => {
        setPapers(data);
        if (data.length > 0) {
          // Match the sidebar's alphabetical ordering so the default selection
          // is always the first paper shown in the list, not API/JSON order.
          const firstAlphabetically = [...data].sort((a, b) => a.title.localeCompare(b.title))[0];
          setSelectedPaper(firstAlphabetically);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load papers"))
      .finally(() => setLoadingPapers(false));
  }, []);

  useEffect(() => {
    if (!selectedPaper) return;
    setAnalyzing(true);
    setAnalysis(null);
    setError(null);
    analyzePaper(selectedPaper)
      .then(setAnalysis)
      .catch((err) => setError(err instanceof Error ? err.message : "Analysis failed"))
      .finally(() => setAnalyzing(false));
  }, [selectedPaper]);

  function handleUploaded(paper: Paper) {
    setPapers((prev) => (prev.some((p) => p.id === paper.id) ? prev : [paper, ...prev]));
    setSelectedPaper(paper);
  }

  return (
    <div className="app-shell">
      <Sidebar papers={papers} selectedPaper={selectedPaper} onSelectPaper={setSelectedPaper} />
      <main className="main-content">
        <header className="app-header">
          <h1>
            <BrandLogo size={36} /> BridgeScout
          </h1>
          <p className="tagline">
            AI-powered cross-domain research gap discovery — extract limitations from a paper, map them to a
            domain-neutral representation, and surface solutions from unrelated research fields.
          </p>
        </header>

        <UploadBar onUploaded={handleUploaded} />

        {loadingPapers && <p className="muted">Loading papers...</p>}
        {error && <p className="error">{error}</p>}

        {selectedPaper && <PaperCard paper={selectedPaper} />}

        {analyzing && <p className="muted">Extracting research gaps and searching other fields...</p>}

        {analysis && !analyzing && <GapTabs gaps={analysis.gaps} />}
      </main>
    </div>
  );
}
