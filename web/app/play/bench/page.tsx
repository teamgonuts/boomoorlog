import BenchMap from "./BenchMap";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Map bench — Boomoorlog",
};

type SearchParams = Promise<{ n?: string }>;

export default async function BenchPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { n } = await searchParams;
  const count = Math.max(1, Math.min(20_000, Number(n ?? 500) || 500));
  return <BenchMap count={count} />;
}
