import { useState, type FormEvent } from "react";
import type { Paper } from "../types";
import { createPaper } from "../api";

interface UploadPaperDialogProps {
  open: boolean;
  domains: string[];
  onClose: () => void;
  onCreated: (paper: Paper) => void;
}

const NEW_DOMAIN = "__new__";

export function UploadPaperDialog({ open, domains, onClose, onCreated }: UploadPaperDialogProps) {
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("");
  const [newDomain, setNewDomain] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [abstract, setAbstract] = useState("");
  const [limitations, setLimitations] = useState("");
  const [method, setMethod] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const chosenDomain = domain === NEW_DOMAIN ? newDomain.trim() : domain;

  function reset() {
    setTitle("");
    setDomain("");
    setNewDomain("");
    setAuthors("");
    setYear("");
    setAbstract("");
    setLimitations("");
    setMethod("");
    setFile(null);
    setError(null);
  }

  function handleClose() {
    if (submitting) return;
    reset();
    onClose();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return setError("Title is required.");
    if (!chosenDomain) return setError("Choose an existing domain or enter a new one.");

    setSubmitting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("title", title.trim());
      form.append("domain", chosenDomain);
      form.append("authors", authors.trim());
      form.append("year", year.trim());
      form.append("abstract", abstract.trim());
      form.append("limitations_text", limitations.trim());
      form.append("method_text", method.trim());
      if (file) form.append("file", file);

      const paper = await createPaper(form);
      onCreated(paper);
      reset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Upload a paper"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h2>Upload a paper</h2>
          <button type="button" className="modal-close" onClick={handleClose} aria-label="Close">
            ×
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <label className="field">
            <span>Title *</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          </label>

          <label className="field">
            <span>Domain *</span>
            <select value={domain} onChange={(e) => setDomain(e.target.value)} required>
              <option value="" disabled>
                Select a domain…
              </option>
              {domains.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
              <option value={NEW_DOMAIN}>＋ New domain…</option>
            </select>
          </label>

          {domain === NEW_DOMAIN && (
            <label className="field">
              <span>New domain name *</span>
              <input
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="e.g. Quantum Computing"
              />
            </label>
          )}

          <div className="field-row">
            <label className="field">
              <span>Authors</span>
              <input value={authors} onChange={(e) => setAuthors(e.target.value)} />
            </label>
            <label className="field">
              <span>Year</span>
              <input
                value={year}
                onChange={(e) => setYear(e.target.value)}
                inputMode="numeric"
                placeholder="2025"
              />
            </label>
          </div>

          <label className="field">
            <span>Abstract</span>
            <textarea rows={3} value={abstract} onChange={(e) => setAbstract(e.target.value)} />
          </label>

          <label className="field">
            <span>Stated limitations / future work</span>
            <textarea rows={3} value={limitations} onChange={(e) => setLimitations(e.target.value)} />
          </label>

          <label className="field">
            <span>Method / solution</span>
            <textarea rows={3} value={method} onChange={(e) => setMethod(e.target.value)} />
          </label>

          <label className="field">
            <span>PDF file</span>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>

          <p className="muted small">
            Blank text fields are filled from the PDF where possible. On save, the paper is stored and
            the search index retrains in the background.
          </p>

          {error && <p className="error small">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn" onClick={handleClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn primary" disabled={submitting}>
              {submitting ? "Saving…" : "Save & train"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
