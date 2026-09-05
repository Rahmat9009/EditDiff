import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EditDiff — Prove every revision landed",
  description: "Evidence-first revision verification for video creators and editors."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
