import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FitPlate Coach",
  description: "Mobile-first nutrition and movement coaching scaffold.",
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
