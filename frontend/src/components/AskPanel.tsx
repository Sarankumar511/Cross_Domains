import { useState, type FormEvent } from "react";
import { askQuestion } from "../api";
import type { AskResponse } from "../types";

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await askQuestion(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card ask-panel">
      <h2>Ask the paper library</h2>
      <p className="muted small">
        Ask a question in plain language. If an uploaded paper contains the answer, the matching
        passages are shown with their source.
      </p>

      <form className="ask-form" onSubmit={handleSubmit}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. How is noisy sensor data handled before classification?"
          aria-label="Question"
        />
        <button type="submit" className="btn primary" disabled={loading}>
          {loading ? "Searching…" : "Ask"}
        </button>
      </form>

      {error && <p className="error small">{error}</p>}

      {result && !result.answer_found && (
        <p className="muted">No information about that was found in the paper library.</p>
      )}

      {result && result.answer_found && (
        <ul className="ask-results">
          {result.matches.map((match, index) => (
            <li key={`${match.paper_id}-${index}`} className="ask-result">
              <p className="ask-snippet">“{match.snippet}”</p>
              <p className="muted small">
                from <strong>{match.paper_title}</strong> · {match.domain} · match{" "}
                {(match.score * 100).toFixed(0)}%
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
