import MapLibrePoc from "./MapLibrePoc";
import { DEFAULT_SPRITE_COUNT } from "../data";

export const metadata = { title: "POC — MapLibre GL" };

type SP = Promise<{ n?: string }>;

export default async function Page({ searchParams }: { searchParams: SP }) {
  const { n } = await searchParams;
  const count = Math.max(1, Math.min(50_000, Number(n) || DEFAULT_SPRITE_COUNT));
  return <MapLibrePoc n={count} />;
}
