import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Business OS",
  description: "Business OS technical foundation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
