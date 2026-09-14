import { create } from "zustand";

export type QueryResult = {
  query_id: string;
  sql: string;
  tables_used: string[];
  reasoning: string;
  rows: Record<string, unknown>[];
  status: string;
  attempts: number;
  answer: string;
};

type QueryState = {
  question: string;
  result: QueryResult | null;
  loading: boolean;
  error: string | null;
  setQuestion: (question: string) => void;
  runQuery: () => Promise<void>;
};

export const useQueryStore = create<QueryState>((set, get) => ({
  question: "",
  result: null,
  loading: false,
  error: null,
  setQuestion: (question) => set({ question }),
  runQuery: async () => {
    const question = get().question.trim();
    if (!question || get().loading) return;

    set({ loading: true, error: null, result: null });
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail.slice(0, 200)}`);
      }
      set({ result: await res.json(), loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },
}));
