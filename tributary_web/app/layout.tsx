import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TRIBUTARY",
  description: "Community matching platform for K-12 literacy professionals",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-body bg-mist min-h-screen">{children}</body>
    </html>
  );
}
