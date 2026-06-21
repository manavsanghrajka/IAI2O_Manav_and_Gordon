import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "Malaria Risk Predictor | AI-Mechanistic Hybrid Model",
  description:
    "Hybrid AI-mechanistic malaria transmission risk predictor using XGBoost climate forecasting and Ross-Macdonald vectorial capacity modeling. By Manav Sanghrajka & Gordon Li.",
  keywords: [
    "malaria",
    "risk prediction",
    "vectorial capacity",
    "Ross-Macdonald",
    "XGBoost",
    "climate forecasting",
    "epidemiology",
  ],
  authors: [
    { name: "Manav Sanghrajka" },
    { name: "Gordon Li" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#0a0e1a] text-[#e2e8f0]">
        {children}
      </body>
    </html>
  );
}
