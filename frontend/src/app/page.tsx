import { ModeToggle } from "@/components/mode-toggle";
import { QueryPanel } from "@/components/query-panel";
import { SchemaBrowser } from "@/components/schema-browser";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight">Text2SQL</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask a question in English. The agent writes the SQL, runs it read-only, and repairs
            itself if the query fails.
          </p>
        </div>
        <ModeToggle />
      </div>

      <div className="mt-8">
        <QueryPanel />
      </div>

      <h2 className="mt-12 font-heading text-lg font-medium">Schema</h2>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Tables and columns you can ask about.
      </p>
      <SchemaBrowser />
    </main>
  );
}
