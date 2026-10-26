export type AnalysisProgress =
  | { type: "stage"; stage: "preparing" | "connecting" | "waiting" | "streaming" | "parsing" | "verifying"; message: string; model?: string; attempt?: number }
  | { type: "delta"; text: string; characters: number; model?: string }
  | { type: "activity"; model?: string };

export type Operation = {
  id: number;
  kind: string;
  subject: string;
  analysis: boolean;
  phase: "running" | "succeeded" | "failed";
  stage: string;
  message: string;
  startedAt: number;
  finishedAt?: number;
  activityAt?: number;
  model?: string;
  attempt: number;
  characters: number;
  preview: string;
  error?: string;
};

// Retain only a Unicode-safe tail; the complete answer belongs to the final result.
export function applyProgress(operation: Operation, event: AnalysisProgress, now: number): Operation {
  if (operation.phase !== "running") return operation;
  const next = { ...operation, model: event.model || operation.model };
  if (event.type === "stage") {
    if (event.attempt !== undefined && event.attempt > next.attempt) {
      next.attempt = event.attempt;
      next.preview = "";
      next.characters = 0;
      next.activityAt = undefined;
    }
    next.stage = event.stage;
    next.message = event.message;
  } else {
    next.activityAt = now;
    if (event.type === "delta") {
      next.preview = Array.from(next.preview + event.text).slice(-1200).join("");
      next.characters = event.characters;
    }
  }
  return next;
}

export function analysisError(result: any, kind: "kill" | "step"): string {
  if (result?.error) return String(result.error);
  if (!result || typeof result !== "object") return "No analysis data returned";
  if (kind === "kill") return Array.isArray(result.steps) || result.summary ? "" : "No kill chain data";
  const description = result.vulnerability?.description;
  // Preserve the existing provider's error-shaped fallback contract.
  if (typeof description === "string" && (/^Analysis generation failed:/.test(description) || /not available for detailed analysis\.$/.test(description))) return description;
  return result.vulnerability || result.attacker_view || result.detection || result.remediation ? "" : "No step detail data";
}
