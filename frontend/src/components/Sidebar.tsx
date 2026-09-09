import { useMemo, useState } from "react";
import type { AdminView } from "../App";
import type { Paper } from "../types";
import { BrandLogo } from "./BrandLogo";

interface SidebarProps {
  isAdmin: boolean;
  adminView: AdminView;
  onAdminViewChange: (view: AdminView) => void;
  papers: Paper[];
  domains: string[];
  loadingPapers: boolean;
  selectedPaper: Paper | null;
  onSelectPaper: (paper: Paper) => void;
  onUploadClick: () => void;
  onCreateDomain: (name: string) => Promise<void> | void;
}

const SPLIT_LABEL: Record<string, string> = {
  train: "train",
  test: "test",
  uploaded: "uploaded",
  sample: "sample",
  corpus: "corpus",
};

/** "SignalProcessing" -> "Signal Processing" for display; grouping still keys on the raw value. */
function humanizeDomain(domain: string): string {
  return domain.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/\s+/g, " ").trim();
}

function groupByDomain(papers: Paper[], allDomains: string[]): [string, Paper[]][] {
  const groups = new Map<string, Paper[]>();
  for (const name of allDomains) {
    if (name.trim()) groups.set(name.trim(), []);
  }
  for (const paper of papers) {
    const key = paper.domain?.trim() || "Uncategorised";
    const bucket = groups.get(key);
    if (bucket) bucket.push(paper);
    else groups.set(key, [paper]);
  }
  return [...groups.entries()]
    .map(([domain, list]) => {
      list.sort((a, b) => {
        const bySplit = (a.split || "").localeCompare(b.split || "");
        return bySplit !== 0 ? bySplit : a.title.localeCompare(b.title);
      });
      return [domain, list] as [string, Paper[]];
    })
    .sort((a, b) => a[0].localeCompare(b[0]));
}

function AnalyzeNote() {
  return (
    <p className="muted small sidebar-note">
      Ask a question on the right, or upload your own paper to run a cross-domain research gap
      analysis.
    </p>
  );
}

export function Sidebar({
  isAdmin,
  adminView,
  onAdminViewChange,
  papers,
  domains,
  loadingPapers,
  selectedPaper,
  onSelectPaper,
  onUploadClick,
  onCreateDomain,
}: SidebarProps) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [creatingDomain, setCreatingDomain] = useState(false);
  const [domainName, setDomainName] = useState("");
  const [domainBusy, setDomainBusy] = useState(false);

  const filteredPapers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return papers;
    return papers.filter(
      (paper) =>
        paper.title.toLowerCase().includes(q) ||
        paper.domain.toLowerCase().includes(q) ||
        (paper.sub_area || "").toLowerCase().includes(q),
    );
  }, [papers, query]);

  const searching = query.trim().length > 0;
  const domainGroups = useMemo(
    () => groupByDomain(filteredPapers, searching ? [] : domains),
    [filteredPapers, domains, searching],
  );

  const totalCount = papers.length;
  const trainCount = papers.filter((p) => p.split === "train").length;
  const testCount = papers.filter((p) => p.split === "test").length;
  const uploadedCount = papers.filter((p) => p.split === "uploaded").length;

  function toggle(domain: string) {
    setExpanded((prev) => ({ ...prev, [domain]: !prev[domain] }));
  }

  async function submitDomain() {
    const name = domainName.trim();
    if (!name) return;
    setDomainBusy(true);
    try {
      await onCreateDomain(name);
      setDomainName("");
      setCreatingDomain(false);
    } finally {
      setDomainBusy(false);
    }
  }

  const showLibrary = isAdmin && adminView === "library";

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>
          <BrandLogo /> BridgeScout
        </h1>
        <p className="tagline">Cross-domain research gap discovery</p>
      </div>
      <hr />

      {isAdmin && (
        <nav className="sidebar-nav" aria-label="Sections">
          <button
            type="button"
            className={`sidebar-nav-item ${adminView === "analyze" ? "active" : ""}`}
            aria-current={adminView === "analyze"}
            onClick={() => onAdminViewChange("analyze")}
          >
            Analyze
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${adminView === "library" ? "active" : ""}`}
            aria-current={adminView === "library"}
            onClick={() => onAdminViewChange("library")}
          >
            Training papers
          </button>
        </nav>
      )}

      {!showLibrary ? (
        <AnalyzeNote />
      ) : (
        <>
          <label className="sidebar-label" htmlFor="paper-search">
            Training papers
          </label>
          <p className="muted small library-summary">
            {totalCount} papers · {trainCount} train · {testCount} test
            {uploadedCount > 0 ? ` · ${uploadedCount} uploaded` : ""}
          </p>

          <div className="library-toolbar">
            <button
              type="button"
              className="btn small"
              onClick={() => setCreatingDomain((value) => !value)}
            >
              + Create domain
            </button>
            <button type="button" className="btn small primary" onClick={onUploadClick}>
              Upload file
            </button>
          </div>

          {creatingDomain && (
            <div className="domain-create">
              <input
                value={domainName}
                onChange={(e) => setDomainName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitDomain()}
                placeholder="New domain name"
                autoFocus
              />
              <button
                type="button"
                className="btn small primary"
                onClick={submitDomain}
                disabled={domainBusy || !domainName.trim()}
              >
                {domainBusy ? "…" : "Add"}
              </button>
            </div>
          )}

          <input
            id="paper-search"
            type="text"
            className="paper-search"
            placeholder="Search papers, domains, sub-areas..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          <div className="paper-tree" role="tree" aria-label="Papers by domain">
            {loadingPapers && <p className="muted small">Loading…</p>}

            {!loadingPapers && domainGroups.length === 0 && (
              <p className="muted small">
                {searching ? `No papers match "${query}".` : "No domains yet."}
              </p>
            )}

            {domainGroups.map(([domain, group]) => {
              const isOpen = searching || !!expanded[domain];
              return (
                <div className="folder" key={domain} role="treeitem" aria-expanded={isOpen}>
                  <button
                    type="button"
                    className="folder-header"
                    onClick={() => toggle(domain)}
                    disabled={searching}
                  >
                    <span className="folder-chevron">{isOpen ? "▾" : "▸"}</span>
                    <span className="folder-name">{humanizeDomain(domain)}</span>
                    <span className="folder-count">{group.length}</span>
                  </button>

                  {isOpen && (
                    <div className="folder-body" role="group">
                      {group.length === 0 && (
                        <p className="muted small folder-empty">No papers yet.</p>
                      )}
                      {group.slice(0, 400).map((paper) => (
                        <button
                          key={paper.id}
                          type="button"
                          role="treeitem"
                          aria-selected={selectedPaper?.id === paper.id}
                          className={`paper-list-item ${
                            selectedPaper?.id === paper.id ? "active" : ""
                          }`}
                          onClick={() => onSelectPaper(paper)}
                          title={paper.title}
                        >
                          {paper.split && (
                            <span className={`split-tag split-${paper.split}`}>
                              {SPLIT_LABEL[paper.split] || paper.split}
                            </span>
                          )}
                          <span className="paper-list-title">{paper.title}</span>
                        </button>
                      ))}
                      {group.length > 400 && (
                        <p className="muted small folder-empty">
                          + {group.length - 400} more — refine the search
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </aside>
  );
}
