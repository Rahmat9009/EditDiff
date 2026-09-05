import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "EditDiff — Prove every revision landed",
  description:
    "Evidence-first revision verification for video creators and editors. Upload the previous and revised export with your notes and get a timestamped PASS / FAIL / REVIEW ledger.",
};

export const viewport: Viewport = {
  themeColor: "#f2f1ec",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
