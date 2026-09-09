import type { Paper } from "../types";
import { DomainBadge } from "./DomainBadge";

interface AnalyzedPaperProps {
  paper: Paper;
  file: File | null;
}

const EXTRACT_CHARS = 700;

/** Compact card for a paper uploaded in the Analyze section: it is analysed on
 * the fly and never stored, so there is no server document to preview - the
 * Download button just hands back the PDF the browser already holds. */
export function AnalyzedPaper({ paper, file }: AnalyzedPaperProps) {
  const meta = [paper.authors, paper.year ? String(paper.year) : "", paper.source]
    .filter(Boolean)
    .join(" · ");
  const extract = (paper.abstract || paper.limitations_text || "").slice(0, EXTRACT_CHARS);
  const truncated = (paper.abstract || paper.limitations_text || "").length > EXTRACT_CHARS;

  function download() {
    if (!file) return;
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.name || `${paper.id}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <section className="card analyzed-paper">
      <div className="analyzed-paper-head">
        <div>
          <h2>{paper.title}</h2>
          <DomainBadge domain={paper.domain} />
          {meta && <p className="muted small analyzed-paper-meta">{meta}</p>}
        </div>
        {file && (
          <button type="button" className="btn" onClick={download}>
            Download
          </button>
        )}
      </div>

      {extract && (
        <div className="paper-section">
          <h3>Extract</h3>
          <p>
            {extract}
            {truncated ? "…" : ""}
          </p>
        </div>
      )}

      <p className="muted small">
        Analysed on the fly — this paper is not saved and not used for training.
      </p>
    </section>
  );
}
