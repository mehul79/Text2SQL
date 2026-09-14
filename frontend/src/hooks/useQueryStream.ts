import { useCallback, useEffect, useReducer, useRef } from "react";

// POST /api/query/stream can't use the browser's EventSource (GET-only, no
// body) — so this reads the same "data: {...}\n\n" SSE framing by hand off a
// fetch() ReadableStream instead.

type NodeName =
  | "understand"
  | "retrieve_schema"
  | "generate_sql"
  | "validate"
  | "execute_sql"
  | "diagnose_error"
  | "repair_sql"
  | "respond";

export type StreamNodeEvent = {
  node: NodeName;
  data: Record<string, unknown>;
};

type Steps = {
  schemaRetrieved: boolean;
  sqlGenerated: boolean;
  validated: boolean;
  executed: boolean;
};

const INITIAL_STEPS: Steps = {
  schemaRetrieved: false,
  sqlGenerated: false,
  validated: false,
  executed: false,
};

export type QueryStreamState = {
  status: "idle" | "streaming" | "done" | "error";
  steps: Steps;
  events: StreamNodeEvent[];
  sql: string;
  attempts: number;
  errors: string[];
  rows: Record<string, unknown>[] | null;
  answer: string | null;
  errorMessage: string | null;
};

const INITIAL_STATE: QueryStreamState = {
  status: "idle",
  steps: INITIAL_STEPS,
  events: [],
  sql: "",
  attempts: 0,
  errors: [],
  rows: null,
  answer: null,
  errorMessage: null,
};

type Action =
  | { type: "start" }
  | { type: "event"; event: StreamNodeEvent }
  | { type: "done" }
  | { type: "error"; message: string };

function reduceEvent(state: QueryStreamState, { node, data }: StreamNodeEvent): QueryStreamState {
  switch (node) {
    case "understand":
      return { ...state, steps: INITIAL_STEPS, attempts: 0, errors: [] };
    case "retrieve_schema":
      return { ...state, steps: { ...state.steps, schemaRetrieved: true } };
    case "generate_sql":
      return {
        ...state,
        steps: { ...state.steps, sqlGenerated: true },
        sql: (data.sql as string) ?? state.sql,
      };
    case "validate": {
      const errors = (data.errors as string[]) ?? [];
      return { ...state, steps: { ...state.steps, validated: errors.length === 0 }, errors };
    }
    case "execute_sql": {
      const errors = (data.errors as string[]) ?? [];
      const executed = errors.length === 0;
      return {
        ...state,
        steps: { ...state.steps, executed },
        errors,
        rows: executed ? (data.result as Record<string, unknown>[]) : state.rows,
      };
    }
    case "diagnose_error":
      return state;
    case "repair_sql":
      // repaired SQL re-enters `validate` from the top — those checks are stale now.
      return {
        ...state,
        steps: { ...state.steps, sqlGenerated: true, validated: false, executed: false },
        sql: (data.sql as string) ?? state.sql,
        attempts: (data.attempts as number) ?? state.attempts,
      };
    case "respond":
      return { ...state, answer: (data.answer as string) ?? null };
    default:
      return state;
  }
}

function reducer(state: QueryStreamState, action: Action): QueryStreamState {
  switch (action.type) {
    case "start":
      return { ...INITIAL_STATE, status: "streaming" };
    case "event":
      return reduceEvent({ ...state, events: [...state.events, action.event] }, action.event);
    case "done":
      return { ...state, status: "done" };
    case "error":
      return { ...state, status: "error", errorMessage: action.message };
  }
}

export function useQueryStream() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  // one connection per component instance — abort whatever's in flight if it
  // unmounts (or a new question starts) rather than let it dangle.
  useEffect(() => () => abortRef.current?.abort(), []);

  const start = useCallback(async (question: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    dispatch({ type: "start" });

    try {
      const res = await fetch("/api/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`${res.status}: ${await res.text()}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split("\n\n");
        buffer = messages.pop() ?? ""; // last chunk may be incomplete — keep it for next read

        for (const message of messages) {
          const payload = message.replace(/^data: /, "");
          if (payload === "[DONE]") {
            dispatch({ type: "done" });
            continue;
          }
          dispatch({ type: "event", event: JSON.parse(payload) });
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      dispatch({ type: "error", message: (e as Error).message });
    }
  }, []);

  return { ...state, start };
}
