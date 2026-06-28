import { supabase } from "@/lib/supabase";

// Always fetch fresh — wiki should reflect DB changes without a rebuild.
export const dynamic = "force-dynamic";

export default async function TestPage() {
  const { count, error } = await supabase
    .from("genera")
    .select("*", { count: "exact", head: true });

  return (
    <main className="min-h-screen p-12 font-mono">
      <h1 className="text-2xl font-bold mb-6">Supabase connection test</h1>
      {error ? (
        <p className="text-red-600">Error: {error.message}</p>
      ) : (
        <p>
          <span className="font-bold">{count}</span> genera rows in the
          database.
        </p>
      )}
      <p className="mt-6 text-sm text-gray-500">
        Expected: 167 (55 fully stat-blocked + 112 sparse).
      </p>
    </main>
  );
}
