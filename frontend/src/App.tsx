import { useEffect, useRef, useState } from "react";
import {
  analyzePaper,
  createDomain,
  getDomains,
  getIndexStatus,
  getMe,
  getPapers,
} from "./api";
import type { AnalyzeResponse, IndexStatus, Me, Paper } from "./types";
import { Sidebar } from "./components/Sidebar";
import { PaperViewer } from "./components/PaperViewer";
import { AnalyzedPaper } from "./components/AnalyzedPaper";
import { GapTabs } from "./components/GapTabs";
import { UploadBar } from "./components/UploadBar";
import { UploadPaperDialog } from "./components/UploadPaperDialog";
import { AskPanel } from "./components/AskPanel";
import { BrandLogo } from "./components/BrandLogo";

export type AdminView = "analyze" | "library";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null);
  const [retrainTick, setRetrainTick] = useState(0);
  // Admin left-panel section: "analyze" is the normal-user view; "library" is
  // the trained-paper browser grouped by domain folder.
  const [adminView, setAdminView] = useState<AdminView>("analyze");

  // --- Analyze section state (kept independently of the library, so switching
  //     tabs and coming back does not lose the upload + its recommendations) ---
  const [paperForAnalysis, setPaperForAnalysis] = useState<Paper | null>(null);
  const [analysisFile, setAnalysisFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  // --- Library section state ---
  const [libraryPaper, setLibraryPaper] = useState<Paper | null>(null);

  const isAdmin = me?.is_admin ?? false;
  const libraryOpen = isAdmin && adminView === "library";
  const pollTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    getMe()
      .then((identity) => {
        setMe(identity);
        if (!identity.is_admin) {
          setLoadingPapers(false);
          return;
        }
        // Only a curator (admin) gets the browsable paper library and domains.
        Promise.all([getPapers(), getDomains().catch(() => [] as string[])])
          .then(([paperList, domainList]) => {
            setPapers(paperList);
            setDomains(domainList);
          })
          .catch((err) => setError(err instanceof Error ? err.message : "Failed to load papers"))
          .finally(() => setLoadingPapers(false));
      })
      .catch(() => {
        setMe({ authenticated: false, is_admin: false });
        setLoadingPapers(false);
      });
  }, []);

  // Run the cross-domain analysis whenever a new paper is uploaded for it.
  useEffect(() => {
    if (!paperForAnalysis) {
      setAnalysis(null);
      return;
    }
    let cancelled = false;
    setAnalyzing(true);
    setAnalysis(null);
    setError(null);
    analyzePaper(paperForAnalysis)
      .then((result) => {
        if (!cancelled) setAnalysis(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Analysis failed");
      })
      .finally(() => {
        if (!cancelled) setAnalyzing(false);
      });
    return () => {
      cancelled = true;
    };
  }, [paperForAnalysis]);

  // Poll the index status while a background retrain is running.
  useEffect(() => {
    if (retrainTick === 0) return;
    let stopped = false;

    const poll = async () => {
      try {
        const status = await getIndexStatus();
        if (stopped) return;
        setIndexStatus(status);
        if (status.state === "training") {
          pollTimer.current = window.setTimeout(poll, 1500);
        }
      } catch {
        /* transient: try again on the next trigger */
      }
    };

    poll();
    return () => {
      stopped = true;
      window.clearTimeout(pollTimer.current);
    };
  }, [retrainTick]);

  function startRetrainWatch() {
    setIndexStatus({ state: "training", papers: 0, passages: 0, error: null });
    setRetrainTick((tick) => tick + 1);
  }

  function handleUploaded(paper: Paper, file: File) {
    setAnalysisFile(file);
    setPaperForAnalysis(paper);
  }

  function handlePaperCreated(paper: Paper) {
    setPapers((prev) => [paper, ...prev.filter((p) => p.id !== paper.id)]);
    setDomains((prev) => (prev.includes(paper.domain) ? prev : [...prev, paper.domain].sort()));
    setLibraryPaper(paper);
    startRetrainWatch();
  }

  function handlePaperDeleted(paperId: string) {
    // The backend filters a deleted paper out of search results immediately, so
    // there is no retrain to wait for here.
    setPapers((prev) => prev.filter((p) => p.id !== paperId));
    setLibraryPaper((prev) => (prev?.id === paperId ? null : prev));
  }

  async function handleCreateDomain(name: string) {
    try {
      setDomains(await createDomain(name));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create domain");
    }
  }

  const training = indexStatus?.state === "training";

  return (
    <div className="app-shell">
      <Sidebar
        isAdmin={isAdmin}
        adminView={adminView}
        onAdminViewChange={setAdminView}
        papers={papers}
        domains={domains}
        loadingPapers={loadingPapers}
        selectedPaper={libraryPaper}
        onSelectPaper={setLibraryPaper}
        onUploadClick={() => setShowUploadDialog(true)}
        onCreateDomain={handleCreateDomain}
      />
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

        {training && (
          <p className="training-banner">Training the search index in the background…</p>
        )}
        {indexStatus?.state === "error" && (
          <p className="error small">Index retrain failed: {indexStatus.error}</p>
        )}

        {libraryOpen ? (
          <>
            {loadingPapers && <p className="muted">Loading the paper library…</p>}
            {error && <p className="error">{error}</p>}
            {libraryPaper ? (
              <PaperViewer paper={libraryPaper} isAdmin onDeleted={handlePaperDeleted} />
            ) : (
              !loadingPapers && (
                <p className="muted">
                  Select a paper from a domain folder on the left to read it and download the source
                  PDF. Use “Upload file” to add a paper for training, or “Create domain” to start a
                  new training domain.
                </p>
              )
            )}
          </>
        ) : (
          <>
            <AskPanel />

            <UploadBar onUploaded={handleUploaded} />

            {error && <p className="error">{error}</p>}

            {paperForAnalysis && (
              <section className="analyze-section">
                <h2 className="section-title">Uploaded paper</h2>
                <AnalyzedPaper paper={paperForAnalysis} file={analysisFile} />
              </section>
            )}

            {paperForAnalysis && (
              <section className="analyze-section">
                <h2 className="section-title">Cross-domain recommendations</h2>
                {analyzing && (
                  <p className="muted">Extracting research gaps and searching other fields…</p>
                )}
                {!analyzing && analysis && <GapTabs gaps={analysis.gaps} />}
                {!analyzing && !analysis && (
                  <p className="muted">No cross-domain recommendations for this paper.</p>
                )}
              </section>
            )}

            {!paperForAnalysis && !analyzing && (
              <p className="muted">
                Ask a question above, or upload a PDF to run a cross-domain research gap analysis.
              </p>
            )}
          </>
        )}
      </main>

      <UploadPaperDialog
        open={showUploadDialog}
        domains={domains}
        onClose={() => setShowUploadDialog(false)}
        onCreated={handlePaperCreated}
      />
    </div>
  );
}
