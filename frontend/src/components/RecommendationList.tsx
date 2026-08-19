import { useCallback, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { Recommendation } from "../types";
import { DomainBadge } from "./DomainBadge";
import { ScoreDonut } from "./ScoreDonut";

interface RecommendationListProps {
  recommendations: Recommendation[];
}

const SCORE_THRESHOLD = 0.5;
const MIN_LIST_WIDTH = 160;
const MAX_LIST_WIDTH = 480;
const DEFAULT_LIST_WIDTH = 260;

export function RecommendationList({ recommendations }: RecommendationListProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [listWidth, setListWidth] = useState(DEFAULT_LIST_WIDTH);
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null);

  const handlePointerMove = useCallback((event: PointerEvent) => {
    if (!dragState.current) return;
    const delta = event.clientX - dragState.current.startX;
    const next = Math.min(MAX_LIST_WIDTH, Math.max(MIN_LIST_WIDTH, dragState.current.startWidth + delta));
    setListWidth(next);
  }, []);

  const handlePointerUp = useCallback(() => {
    dragState.current = null;
    document.body.classList.remove("resizing-columns");
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
  }, [handlePointerMove]);

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    dragState.current = { startX: event.clientX, startWidth: listWidth };
    document.body.classList.add("resizing-columns");
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  if (recommendations.length === 0) {
    return <p className="muted">No cross-domain candidates found.</p>;
  }

  const active = recommendations[Math.min(activeIndex, recommendations.length - 1)];

  return (
    <div className="rec-split">
      <div className="rec-list" style={{ width: listWidth }} role="listbox" aria-label="Cross-domain recommendations">
        {recommendations.map((rec, index) => (
          <button
            key={rec.title}
            type="button"
            role="option"
            aria-selected={index === activeIndex}
            className={`rec-list-item ${index === activeIndex ? "active" : ""}`}
            onClick={() => setActiveIndex(index)}
          >
            <span
              className={`rec-list-dot ${rec.bridge_score >= SCORE_THRESHOLD ? "high" : "low"}`}
              aria-hidden="true"
            />
            <span className="rec-list-text">
              <span className="rec-list-title">
                {index + 1}. {rec.title}
              </span>
              <span className="rec-list-domain">{rec.domain}</span>
            </span>
          </button>
        ))}
      </div>

      <div
        className="rec-splitter"
        onPointerDown={handlePointerDown}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize recommendation list"
      />

      <div className="rec-detail">
        <div className="rec-detail-main">
          <h4>{active.title}</h4>
          <DomainBadge domain={active.domain} />
          <p>{active.method_text}</p>
          <p className="muted small">{active.rationale}</p>
          <p className="muted small">Similarity: {active.similarity.toFixed(2)}</p>
        </div>
        <div className="rec-detail-score">
          <span className="score-label">Bridge Score</span>
          <ScoreDonut score={active.bridge_score} />
          <span className="muted small">{active.status_label}</span>
        </div>
      </div>
    </div>
  );
}
