import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: {
    default: "EditDiff — Regression testing for video production",
    template: "%s",
  },
  description:
    "Catch missed revisions and accidental changes before they ship. EditDiff verifies requested revisions, detects accidental changes, and runs final release QA between video exports.",
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
