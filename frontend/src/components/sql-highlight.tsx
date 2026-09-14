import { cn } from "@/lib/utils";

// hand-rolled instead of pulling in a highlighter package — the queries here
// are single-statement and small, a regex tokenizer is plenty.
const KEYWORDS = new Set([
  "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "AS", "JOIN", "LEFT", "RIGHT",
  "INNER", "OUTER", "ON", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "WITH",
  "INSERT", "UPDATE", "DELETE", "VALUES", "SET", "INTO", "DISTINCT", "COUNT",
  "SUM", "AVG", "MIN", "MAX", "ASC", "DESC", "IN", "IS", "NULL", "LIKE",
  "BETWEEN", "UNION", "ALL", "CASE", "WHEN", "THEN", "ELSE", "END",
]);

type Token = { text: string; kind: "keyword" | "string" | "number" | "plain" };

const TOKEN_RE = /('[^']*')|(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\s+)|([(),;.*=<>!+-])/g;

function tokenize(sql: string): Token[] {
  const tokens: Token[] = [];
  let match: RegExpExecArray | null;
  TOKEN_RE.lastIndex = 0;
  while ((match = TOKEN_RE.exec(sql))) {
    const [text, str, num, word] = match;
    if (str) tokens.push({ text, kind: "string" });
    else if (num) tokens.push({ text, kind: "number" });
    else if (word) tokens.push({ text, kind: KEYWORDS.has(word.toUpperCase()) ? "keyword" : "plain" });
    else tokens.push({ text, kind: "plain" });
  }
  return tokens;
}

export function SqlHighlight({ sql, className }: { sql: string; className?: string }) {
  return (
    <pre className={cn("overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs", className)}>
      {tokenize(sql).map((t, i) => {
        if (t.kind === "keyword") {
          return (
            <span key={i} className="font-semibold text-blue-600 dark:text-blue-400">
              {t.text}
            </span>
          );
        }
        if (t.kind === "string") {
          return (
            <span key={i} className="text-emerald-600 dark:text-emerald-400">
              {t.text}
            </span>
          );
        }
        if (t.kind === "number") {
          return (
            <span key={i} className="text-amber-600 dark:text-amber-400">
              {t.text}
            </span>
          );
        }
        return <span key={i}>{t.text}</span>;
      })}
    </pre>
  );
}
