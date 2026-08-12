import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Evaluation Lab — RAGAS vs DeepEval",
  description: "Evidence-first comparison dashboard for Exercise 3.4.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
