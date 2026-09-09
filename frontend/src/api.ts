import type { AnalyzeResponse, AskResponse, IndexStatus, Me, Paper } from "./types";

// Same-origin by default: on SAP BTP the Work Zone approuter routes "/api/*" to
// the backend via the "bridgescout-srv-api" destination; in local dev Vite
// proxies "/api" to http://localhost:8000 (see vite.config.ts). Override with
// VITE_API_BASE for a non-proxied setup.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${path} failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function getMe(): Promise<Me> {
  return requestJson<Me>("/api/me");
}

export async function getPapers(): Promise<Paper[]> {
  // Curator-only endpoint: a non-admin caller gets 403 -> treat as "no library".
  const response = await fetch(`${API_BASE}/api/papers`);
  if (response.status === 403) return [];
  if (!response.ok) {
    throw new Error(`/api/papers failed (${response.status}): ${await response.text()}`);
  }
  return response.json() as Promise<Paper[]>;
}

export function paperFileUrl(paperId: string, download = false): string {
  const suffix = download ? "?download=1" : "";
  return `${API_BASE}/api/papers/${encodeURIComponent(paperId)}/file${suffix}`;
}

export async function deletePaper(paperId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/papers/${encodeURIComponent(paperId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`delete failed (${response.status}): ${await response.text()}`);
  }
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

export function getDomains(): Promise<string[]> {
  return requestJson<string[]>("/api/domains");
}

export function createDomain(name: string): Promise<string[]> {
  return requestJson<string[]>("/api/domains", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function createPaper(form: FormData): Promise<Paper> {
  return requestJson<Paper>("/api/papers", { method: "POST", body: form });
}

export function getIndexStatus(): Promise<IndexStatus> {
  return requestJson<IndexStatus>("/api/index/status");
}

export function askQuestion(question: string): Promise<AskResponse> {
  return requestJson<AskResponse>("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
