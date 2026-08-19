import { useState } from "react";
import type { GapResult } from "../types";
import { RecommendationList } from "./RecommendationList";

interface GapTabsProps {
  gaps: GapResult[];
}

export function GapTabs({ gaps }: GapTabsProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (gaps.length === 0) {
    return <p className="muted">No gaps detected in this paper.</p>;
  }

  const active = gaps[Math.min(activeIndex, gaps.length - 1)];

  return (
    <div>
      <h3>Detected Research Gaps</h3>
      <p className="muted small">
        Each tab is one unresolved problem or future-work statement found in the paper.
      </p>

      <div className="tabs gap-tabs">
        <div className="tab-bar" role="tablist">
          {gaps.map((gap, index) => (
            <button
              key={gap.index}
              type="button"
              role="tab"
              aria-selected={index === activeIndex}
              className={`tab-button ${index === activeIndex ? "active" : ""}`}
              onClick={() => setActiveIndex(index)}
              title={gap.headline}
            >
              {index + 1}. {gap.short_title}
            </button>
          ))}
        </div>

        <div className="tab-panel">
          <div className="card gap-card">
            <strong>{active.headline}</strong>
            <p className="gap-text">{active.text}</p>
          </div>

          <h4>Cross-Domain Recommendations</h4>
          <p className="muted small">
            Domain-neutral problem statement: <em>{active.generic_text}</em>
          </p>

          <RecommendationList recommendations={active.recommendations} />
        </div>
      </div>
    </div>
  );
}
