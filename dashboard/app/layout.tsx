import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
  title: "Content Intel",
  description: "Reddit + HN → leads and drafts",
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
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <nav className="border-b px-6 py-3 flex gap-6 text-sm font-medium">
          <a href="/" className="hover:text-foreground/70 transition-colors">Feed</a>
          <a href="/leads" className="hover:text-foreground/70 transition-colors">Leads</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
