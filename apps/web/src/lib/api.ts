import type { HealthResponse, ReadinessResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  const response = await fetch(`${API_URL}/api/v1/system/readiness`, {
    cache: "no-store",
  });

  const data = (await response.json()) as ReadinessResponse;

  if (!response.ok && response.status !== 200) {
    throw new Error(data.status ?? `Readiness failed: ${response.status}`);
  }

  return data;
}

export function getApiUrl(): string {
  return API_URL;
}
