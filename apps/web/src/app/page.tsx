"use client";

import { useEffect, useState } from "react";

import { SystemStatus } from "@/components/system-status";
import { fetchHealth, fetchReadiness } from "@/lib/api";
import type { ReadinessResponse, UiState } from "@/lib/types";

export default function HomePage() {
  const [uiState, setUiState] = useState<UiState>("loading");
  const [apiReachable, setApiReachable] = useState(false);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | undefined>();

  useEffect(() => {
    let active = true;

    async function load() {
      setUiState("loading");
      setErrorMessage(undefined);

      try {
        await fetchHealth();
        if (!active) return;
        setApiReachable(true);

        const data = await fetchReadiness();
        if (!active) return;
        setReadiness(data);

        if (data.status === "ready") {
          setUiState("ready");
        } else if (data.status === "partial") {
          setUiState("partial");
        } else {
          setUiState("error");
        }
      } catch (error) {
        if (!active) return;
        setApiReachable(false);
        setReadiness(null);
        setUiState("error");
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load system status",
        );
      }
    }

    load();
    const interval = setInterval(load, 15000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 8 }}>Business OS</h1>
      <p style={{ color: "#64748b", marginBottom: 24 }}>
        Technical foundation status — API, PostgreSQL, Redis and MinIO.
      </p>
      <SystemStatus
        uiState={uiState}
        apiReachable={apiReachable}
        components={readiness?.components}
        errorMessage={errorMessage}
      />
    </main>
  );
}
