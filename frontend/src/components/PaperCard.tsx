import type { Paper } from "../types";
import { DomainBadge } from "./DomainBadge";

interface PaperCardProps {
  paper: Paper;
}

export function PaperCard({ paper }: PaperCardProps) {
  return (
    <div className="card paper-card">
      <h2>{paper.title}</h2>
      <DomainBadge domain={paper.domain} />
      {paper.abstract && <p>{paper.abstract}</p>}
    </div>
  );
}
