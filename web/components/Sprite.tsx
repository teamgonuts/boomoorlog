import Image from "next/image";

/**
 * Pixel-art tree sprite. Files live at web/public/sprites/<slug>.png; the
 * source-of-truth copy is data/sprites_pixel/ (Python pipeline output) and
 * mirrored here so Vercel can build the app from web/ alone. Always rendered
 * with crisp upscaling (no bilinear blur).
 */
export function Sprite({
  slug,
  size = 48,
  className = "",
}: {
  slug: string;
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={`shrink-0 inline-block bg-stone-100 rounded ${className}`}
      style={{ width: size, height: size }}
    >
      <Image
        src={`/sprites/${slug}.png`}
        alt={`${slug} sprite`}
        width={size}
        height={size}
        className="pixelated"
        unoptimized
      />
    </div>
  );
}
