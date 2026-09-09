import { useState } from "react";
import type { Paper } from "../types";
import { deletePaper, paperFileUrl } from "../api";
import { DomainBadge } from "./DomainBadge";

interface PaperViewerProps {
  paper: Paper;
  isAdmin: boolean;
  onDeleted: (paperId: string) => void;
}

export function PaperViewer({ paper, isAdmin, onDeleted }: PaperViewerProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meta = [paper.authors, paper.year ? String(paper.year) : "", paper.source]
    .filter(Boolean)
    .join(" · ");

  async function handleDelete() {
    if (!window.confirm(`Delete "${paper.title}" from the paper library?`)) return;
    setDeleting(true);
    setError(null);
    try {
      await deletePaper(paper.id);
      onDeleted(paper.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  }

  return (
    <div className="card paper-viewer">
      <div className="paper-viewer-head">
        <div>
          <h2>{paper.title}</h2>
          <DomainBadge domain={paper.domain} />
          {meta && <p className="muted small paper-viewer-meta">{meta}</p>}
        </div>

        {isAdmin && (
          <div className="paper-toolbar">
            <a className="btn" href={paperFileUrl(paper.id, true)}>
              Download
            </a>
            <button
              type="button"
              className="btn danger"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        )}
      </div>

      {error && <p className="error small">{error}</p>}

      {paper.abstract && (
        <div className="paper-section">
          <h3>Abstract</h3>
          <p>{paper.abstract}</p>
        </div>
      )}

      {paper.limitations_text && paper.limitations_text !== paper.abstract && (
        <div className="paper-section">
          <h3>Stated limitations / future work</h3>
          <p>{paper.limitations_text}</p>
        </div>
      )}

      {paper.method_text && (
        <div className="paper-section">
          <h3>Method / solution</h3>
          <p>{paper.method_text}</p>
        </div>
      )}

      {isAdmin && (
        <div className="paper-section">
          <h3>Document</h3>
          <iframe
            className="paper-frame"
            src={paperFileUrl(paper.id)}
            title={`Document: ${paper.title}`}
          />
        </div>
      )}
    </div>
  );
}
