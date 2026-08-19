import type { AnalyzeResponse, Paper } from "./types";

const API_BASE = "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${path} failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function getPapers(): Promise<Paper[]> {
  return requestJson<Paper[]>("/api/papers");
}

export function analyzePaper(paper: Paper): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper }),
  });
}

export async function uploadPaper(file: File, domain: string): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("domain", domain);
  return requestJson<Paper>("/api/papers/upload", {
    method: "POST",
    body: formData,
  });
}
