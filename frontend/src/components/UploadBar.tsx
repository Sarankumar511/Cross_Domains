import { useState, type ChangeEvent } from "react";
import type { Paper } from "../types";
import { uploadPaper } from "../api";

interface UploadBarProps {
  onUploaded: (paper: Paper, file: File) => void;
}

export function UploadBar({ onUploaded }: UploadBarProps) {
  const [domain, setDomain] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setUploading(true);
    setError(null);
    try {
      const paper = await uploadPaper(file, domain.trim() || "Unknown");
      onUploaded(paper, file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="upload-bar">
      <span className="upload-bar-title">Have your own paper?</span>

      <div className="upload-bar-field">
        <label htmlFor="upload-bar-domain">Domain</label>
        <input
          id="upload-bar-domain"
          type="text"
          placeholder="e.g. Computer Science"
          value={domain}
          onChange={(event) => setDomain(event.target.value)}
        />
      </div>

      <div className="upload-bar-action">
        {fileName && !error && <span className="muted small">{fileName}</span>}
        {error && <span className="error small">{error}</span>}

        <label htmlFor="upload-bar-file" className={`upload-bar-button ${uploading ? "disabled" : ""}`}>
          {uploading ? "Uploading..." : "Upload"}
        </label>
        <input
          id="upload-bar-file"
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          disabled={uploading}
          className="upload-bar-input"
        />
      </div>
    </div>
  );
}
