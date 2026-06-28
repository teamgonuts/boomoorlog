import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Creatures — Amsterdam",
  description:
    "Defend your Amsterdam neighborhood against waves of urban creatures — your real trees are the towers.",
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
                stroke="#22c55e"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M15 4 C17 4 19 6 19 8 L20.5 8 L19 9.5 L18 9 C18 12 17 15 15 17 L12 22 L11 22 L9 17 C8 14 8 10 10 8 C11 6 13 4 15 4 Z" />
                <circle cx="17" cy="6.5" r="0.7" fill="#22c55e" stroke="none" />
              </svg>
            </span>
            <span className="brand-name">Creatures</span>
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
