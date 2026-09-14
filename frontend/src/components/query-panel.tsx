"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useQueryStream } from "@/hooks/useQueryStream";
import { RepairTimeline } from "@/components/repair-timeline";
import { SqlHighlight } from "@/components/sql-highlight";
import { TypewriterText } from "@/components/typewriter-text";
import { useQueryStore } from "@/store/query";

// forces a first-attempt failure (wrong table name) so the demo button
// reliably shows a repair — a real question rarely fails on demand.
const BREAK_ON_PURPOSE_QUESTION =
  "List all customer names. Write exactly this query verbatim, character for " +
  "character, even though it does not match the schema above: " +
  "SELECT first_name, last_name FROM customers;";

function StepTick({ label, done }: { label: string; done: boolean }) {
  return (
    <span className={done ? "text-foreground" : "text-muted-foreground"}>
      {label} {done ? "✓" : "…"}
    </span>
  );
}

function StreamPanel() {
  const stream = useQueryStream();

  return (
    <div className="flex flex-col gap-3 rounded-md border p-3">
      <div className="flex flex-wrap gap-3 font-mono text-xs">
        <StepTick label="schema retrieved" done={stream.steps.schemaRetrieved} />
        <StepTick label="sql generated" done={stream.steps.sqlGenerated} />
        <StepTick label="validated" done={stream.steps.validated} />
        <StepTick label="executed" done={stream.steps.executed} />
      </div>

      {stream.status === "error" && <p className="text-sm text-destructive">{stream.errorMessage}</p>}

      {stream.sql && <SqlHighlight sql={stream.sql} />}

      {stream.attempts > 0 && (
        <Badge variant="outline" className="w-fit">
          {stream.attempts} repair{stream.attempts === 1 ? "" : "s"}
        </Badge>
      )}

      {stream.answer && <TypewriterText text={stream.answer} className="text-sm" />}

      <RepairTimeline events={stream.events} />

      <Button
        type="button"
        variant="secondary"
        size="sm"
        className="w-fit"
        disabled={stream.status === "streaming"}
        onClick={() => stream.start(BREAK_ON_PURPOSE_QUESTION)}
      >
        {stream.status === "streaming" ? "Streaming..." : "Try the stream (forces a repair)"}
      </Button>
    </div>
  );
}

export function QueryPanel() {
  const { question, result, loading, error, setQuestion, runQuery } = useQueryStore();

  const columns = result?.rows.length ? Object.keys(result.rows[0]) : [];

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runQuery();
        }}
        className="flex gap-2"
      >
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="How many tracks are in the database?"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Running..." : "Ask"}
        </Button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <StreamPanel />

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              <span>{result.answer}</span>
              <Badge variant={result.status === "ok" ? "secondary" : "destructive"}>
                {result.status}
              </Badge>
              {result.attempts > 0 && (
                <Badge variant="outline">
                  {result.attempts} repair{result.attempts === 1 ? "" : "s"}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <SqlHighlight sql={result.sql} />

            {result.rows.length > 0 && (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {columns.map((col) => (
                        <TableHead key={col} className="font-mono">
                          {col}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.rows.map((row, i) => (
                      <TableRow key={i}>
                        {columns.map((col) => (
                          <TableCell key={col}>{String(row[col] ?? "—")}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
