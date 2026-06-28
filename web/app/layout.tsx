import type { Metadata } from "next";
import { Montserrat, Raleway } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-display",
  display: "swap",
});
const raleway = Raleway({
  subsets: ["latin"],
  weight: ["300", "400", "700"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Creatures — Amsterdam",
  description:
    "Defend your Amsterdam neighborhood against waves of urban creatures — your real trees are the towers.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${montserrat.variable} ${raleway.variable}`}>
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              <svg
                width="28"
                height="28"
                viewBox="0 0 32 32"
                fill="none"
                stroke="none"
              >
                {/* Ring-necked parakeet, facing right: round head, hooked
                    beak, long pointed tail. Mint silhouette. */}
                <path
                  fill="#30ffbb"
                  d="M22 7
                     C24 7 26 8 26.5 9
                     L29 12
                     L26.5 13
                     C25 14 24 14.5 23 14.5
                     C23 17 21 19 17 20
                     L11 19
                     L2 22
                     L5 19
                     C7 17 9 16 11 15
                     C12 12 14 9 17 8
                     C19 7 21 7 22 7 Z"
                />
                <circle cx="22" cy="11" r="0.95" fill="#0e1514" />
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
            <Link href="/observations" className="nav-link">
              Observations
            </Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
