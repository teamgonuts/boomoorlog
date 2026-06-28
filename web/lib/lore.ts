/**
 * Parse the per-genus lore markdown (stored in `genera.lore`) into
 * structured sections the detail page can render:
 *   - combatFlavor: the paragraph under `## Combat flavor`
 *   - facts: list of {key, value} from `## Real-world facts` bullets
 *           (e.g. "- **Typical / max height:** 20–40 m typical…")
 *
 * Source MD is hand-authored in memory/characters/<slug>.md and ingested
 * verbatim by seed_genera.py. Anything we can't parse silently degrades to
 * empty / dropped.
 */

export type Fact = { key: string; value: string };

export type ParsedLore = {
  combatFlavor: string;
  facts: Fact[];
  commonName: string | null;
};

const FACT_BULLET = /^-\s+\*\*(.+?):\*\*\s+(.+)$/;
// H1 line: `# Tilia — Linden (Linde)` → commonName "Linden"
const TITLE_LINE = /^#\s+\S+\s*[—\-]\s*([^()]+?)\s*(?:\(|$)/m;

export function parseLore(raw: string | null | undefined): ParsedLore {
  if (!raw) return { combatFlavor: "", facts: [], commonName: null };

  const titleMatch = raw.match(TITLE_LINE);
  const commonName = titleMatch ? titleMatch[1].trim() : null;

  const sections = new Map<string, string>();
  for (const part of raw.split(/^## /m).slice(1)) {
    const nl = part.indexOf("\n");
    const heading = (nl >= 0 ? part.slice(0, nl) : part).trim().toLowerCase();
    const body = (nl >= 0 ? part.slice(nl + 1) : "").trim();
    sections.set(heading, body);
  }

  const facts: Fact[] = [];
  for (const line of (sections.get("real-world facts") ?? "").split("\n")) {
    const m = line.match(FACT_BULLET);
    if (m) facts.push({ key: m[1].trim(), value: m[2].trim() });
  }

  return {
    combatFlavor: sections.get("combat flavor") ?? "",
    facts,
    commonName,
  };
}
