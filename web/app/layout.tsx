import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Boomoorlog — Amsterdam tree-war",
  description:
    "Two Amsterdam ZIP codes battle tower-defense style using the real trees that grow in each postcode.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <nav className="bg-white border-b border-stone-200">
          <div className="max-w-6xl mx-auto px-8 md:px-12 py-3 flex items-center gap-6 text-sm">
            <Link href="/" className="font-semibold">
              🌳 Boomoorlog
            </Link>
            <Link
              href="/wiki"
              className="text-gray-600 hover:text-emerald-700"
            >
              Wiki
            </Link>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
