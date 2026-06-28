import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Boomoorlog — Amsterdam tree-war",
  description:
    "Two Amsterdam ZIP codes battle tower-defense style using the real trees that grow in each postcode.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            🌳 Boomoorlog <span>Wiki</span>
          </Link>
          <span className="tagline">The trees of Amsterdam, ready for war</span>
          <Link href="/play" className="nav-link" style={{ marginLeft: "auto" }}>
            Play
          </Link>
          <Link href="/wiki/trees" className="nav-link">
            All trees
          </Link>
          <Link href="/wiki/creatures" className="nav-link">
            All creatures
          </Link>
        </header>
        {children}
      </body>
    </html>
  );
}
