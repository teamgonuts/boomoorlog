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
            <span className="brand-mark" aria-hidden="true">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2 4 12h3l-3 5h5v5h6v-5h5l-3-5h3z" />
              </svg>
            </span>
            <span className="brand-name">Boomoorlog</span>
          </Link>
          <nav className="site-nav">
            <Link href="/play" className="nav-link">
              Play
            </Link>
            <Link href="/wiki/trees" className="nav-link">
              Trees
            </Link>
            <Link href="/wiki/creatures" className="nav-link">
              Creatures
            </Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
