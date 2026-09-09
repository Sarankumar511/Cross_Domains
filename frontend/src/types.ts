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
  // Present on the /api/papers listing: "train" | "test" (collected corpus),
  // "uploaded" (admin), "sample" (bundled seed), "" otherwise.
  split?: string;
  sub_area?: string;
}

export interface Me {
  authenticated: boolean;
  is_admin: boolean;
}

export interface IndexStatus {
  state: "ready" | "training" | "error";
  papers: number;
  passages: number;
  error: string | null;
}

export interface AskMatch {
  paper_id: string;
  paper_title: string;
  domain: string;
  snippet: string;
  score: number;
}

export interface AskResponse {
  question: string;
  answer_found: boolean;
  matches: AskMatch[];
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
