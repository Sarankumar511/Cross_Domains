import { useMemo, useState } from "react";
import type { Paper } from "../types";
import { BrandLogo } from "./BrandLogo";

interface SidebarProps {
  papers: Paper[];
  selectedPaper: Paper | null;
  onSelectPaper: (paper: Paper) => void;
}

export function Sidebar({ papers, selectedPaper, onSelectPaper }: SidebarProps) {
  const [query, setQuery] = useState("");

  const filteredPapers = useMemo(() => {
    const sorted = [...papers].sort((a, b) => a.title.localeCompare(b.title));
    const q = query.trim().toLowerCase();
    if (!q) return sorted;
    return sorted.filter((paper) => paper.title.toLowerCase().includes(q));
  }, [papers, query]);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>
          <BrandLogo /> BridgeScout
        </h1>
        <p className="tagline">Cross-domain research gap discovery</p>
      </div>
      <hr />

      <label className="sidebar-label" htmlFor="paper-search">
        Paper
      </label>
      <input
        id="paper-search"
        type="text"
        className="paper-search"
        placeholder="Search papers..."
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      <div className="paper-list" role="listbox" aria-label="Papers">
        {filteredPapers.length === 0 && <p className="muted small">No papers match "{query}".</p>}
        {filteredPapers.map((paper) => (
          <button
            key={paper.id}
            type="button"
            role="option"
            aria-selected={selectedPaper?.id === paper.id}
            className={`paper-list-item ${selectedPaper?.id === paper.id ? "active" : ""}`}
            onClick={() => onSelectPaper(paper)}
          >
            {paper.title}
          </button>
        ))}
      </div>
    </aside>
  );
}
