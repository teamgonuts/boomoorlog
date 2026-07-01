/**
 * /organism_photos/[slug] — Serves C5-backfilled organism photos from
 * `data/organism_photos/` (outside web/public, so Turbopack won't try
 * to bundle them). Used by /sprites QA page today; likely also used by
 * public routes once the encyclopedia goes live.
 *
 * URLs look like `/organism_photos/abia-nitens.jpg` — the [slug] segment
 * is the full filename including extension.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { NextRequest } from "next/server";

const DATA_DIR = path.join(process.cwd(), "..", "data", "organism_photos");

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  // Guard against path traversal
  if (slug.includes("/") || slug.includes("..")) {
    return new Response("Bad request", { status: 400 });
  }
  const filePath = path.join(DATA_DIR, slug);
  try {
    const buf = await fs.readFile(filePath);
    const contentType = slug.toLowerCase().endsWith(".png")
      ? "image/png"
      : "image/jpeg";
    return new Response(buf as unknown as BodyInit, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
