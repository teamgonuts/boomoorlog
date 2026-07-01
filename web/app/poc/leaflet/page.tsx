import LeafletPoc from "./LeafletPoc";
import { DEFAULT_SPRITE_COUNT } from "../data";

export const metadata = { title: "POC — Leaflet + canvas overlay" };

type SP = Promise<{ n?: string }>;

export default async function Page({ searchParams }: { searchParams: SP }) {
  const { n } = await searchParams;
  const count = Math.max(1, Math.min(50_000, Number(n) || DEFAULT_SPRITE_COUNT));
  return <LeafletPoc n={count} />;
}
