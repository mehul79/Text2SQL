import { create } from "zustand";

export type Column = {
  name: string;
  type: string;
  foreign_key: string | null;
};

type SchemaState = {
  tables: Record<string, Column[]> | null;
  error: string | null;
  fetchSchema: () => Promise<void>;
};

export const useSchemaStore = create<SchemaState>((set) => ({
  tables: null,
  error: null,
  fetchSchema: async () => {
    try {
      const res = await fetch("/api/schema");
      if (!res.ok) throw new Error(`GET /api/schema returned ${res.status}`);
      const data = await res.json();
      set({ tables: data.tables, error: null });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },
}));
