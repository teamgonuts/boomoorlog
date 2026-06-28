import Image from "next/image";

/**
 * Pixel-art tree sprite. Symlinked from data/sprites_pixel/<slug>.png to
 * web/public/sprites/<slug>.png at install time. Always rendered with
 * crisp upscaling (no bilinear blur).
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
