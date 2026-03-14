import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "TRIBUTARY — Upstream Literacy",
    template: "%s | TRIBUTARY",
  },
  description:
    "Community matching platform connecting K-12 literacy professionals across districts to collaborate on shared challenges.",
  keywords: ["literacy", "K-12", "education", "community", "matching"],
  robots: "noindex, nofollow",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a1628",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-body bg-mist min-h-screen antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-current focus:text-white focus:px-4 focus:py-2 focus:rounded-input focus:text-sm focus:font-bold"
        >
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
