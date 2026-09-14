import { Badge } from "@/components/ui/badge";
import { SqlHighlight } from "@/components/sql-highlight";
import type { StreamNodeEvent } from "@/hooks/useQueryStream";

type Attempt = { sql: string; error: string | null };

function buildAttempts(events: StreamNodeEvent[]): Attempt[] {
  const attempts: Attempt[] = [];

  for (const { node, data } of events) {
    if (node === "generate_sql" || node === "repair_sql") {
      attempts.push({ sql: (data.sql as string) ?? "", error: null });
      continue;
    }
    if (node === "validate" || node === "execute_sql") {
      const errors = (data.errors as string[]) ?? [];
      if (errors.length > 0 && attempts.length > 0) {
        attempts[attempts.length - 1].error = errors[errors.length - 1];
      }
    }
  }

  return attempts;
}

type DiffToken = { text: string; kind: "same" | "removed" | "added" };

// word-level LCS diff — small enough to hand-roll for single-line SQL, and this
// is the one view meant to explain the whole project, so it earns the diff.
function diffWords(before: string, after: string): DiffToken[] {
  const a = before.split(/(\s+)/);
  const b = after.split(/(\s+)/);
  const dp: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));

  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const tokens: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      tokens.push({ text: b[j], kind: "same" });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      tokens.push({ text: a[i], kind: "removed" });
      i++;
    } else {
      tokens.push({ text: b[j], kind: "added" });
      j++;
    }
  }
  while (i < a.length) tokens.push({ text: a[i++], kind: "removed" });
  while (j < b.length) tokens.push({ text: b[j++], kind: "added" });

  return tokens;
}

function DiffLine({ tokens }: { tokens: DiffToken[] }) {
  return (
    <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
      {tokens.map((t, i) => {
        if (t.kind === "same") return <span key={i}>{t.text}</span>;
        if (t.kind === "removed") {
          return (
            <span key={i} className="text-destructive line-through">
              {t.text}
            </span>
          );
        }
        return (
          <span key={i} className="text-emerald-600 underline dark:text-emerald-400">
            {t.text}
          </span>
        );
      })}
    </pre>
  );
}

export function RepairTimeline({ events }: { events: StreamNodeEvent[] }) {
  const attempts = buildAttempts(events);
  if (attempts.length < 2) return null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium">Repair timeline</p>
      {attempts.map((attempt, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-md border p-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Attempt {i + 1}</span>
            <Badge variant={attempt.error ? "destructive" : "secondary"}>
              {attempt.error ? "failed" : "succeeded"}
            </Badge>
          </div>

          {i === 0 ? (
            <SqlHighlight sql={attempt.sql} />
          ) : (
            <DiffLine tokens={diffWords(attempts[i - 1].sql, attempt.sql)} />
          )}

          {attempt.error && <p className="text-xs text-destructive">{attempt.error}</p>}
        </div>
      ))}
    </div>
  );
}
