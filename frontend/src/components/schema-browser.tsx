"use client";

import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSchemaStore } from "@/store/schema";

export function SchemaBrowser() {
  const { tables, error, fetchSchema } = useSchemaStore();

  useEffect(() => {
    fetchSchema();
  }, [fetchSchema]);

  return (
    <div className="flex flex-col gap-6">
      {error && <p className="text-sm text-destructive">Could not load schema: {error}</p>}

      {!tables &&
        !error &&
        Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}

      {tables && Object.keys(tables).length === 0 && (
        <p className="text-sm text-muted-foreground">
          The database has no tables. Load the Chinook data, then reload this page.
        </p>
      )}

      {tables &&
        Object.entries(tables).map(([tableName, columns]) => (
          <Card key={tableName}>
            <CardHeader>
              <CardTitle className="font-mono">{tableName}</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Column</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>References</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {columns.map((col) => (
                    <TableRow key={col.name}>
                      <TableCell className="font-mono">{col.name}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{col.type}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-muted-foreground">
                        {col.foreign_key ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}
    </div>
  );
}
