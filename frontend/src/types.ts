export interface Paper {
  id: string;
  title: string;
  domain: string;
  abstract: string;
  authors: string;
  year: number | null;
  limitations_text: string;
  method_text: string;
  source: string;
}

export interface Candidate {
  title: string;
  domain: string;
  similarity: number;
}

export interface Recommendation {
  title: string;
  short_title: string;
  domain: string;
  similarity: number;
  domain_bonus: number;
  bridge_score: number;
  rationale: string;
  method_text: string;
  status_label: string;
}

export interface GapResult {
  index: number;
  text: string;
  short_title: string;
  headline: string;
  generic_text: string;
  candidates: Candidate[];
  recommendations: Recommendation[];
}

export interface AnalyzeResponse {
  gaps: GapResult[];
}
