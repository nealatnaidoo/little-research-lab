import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Press_Start_2P } from "next/font/google";
import "./globals.css";

// Clean, readable sans-serif for body
const sansFont = Inter({
  variable: "--font-terminal",
  subsets: ["latin"],
  display: "swap",
});

// Monospace for code
const monoFont = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

// Pixel font - used sparingly for retro accents
const arcadeFont = Press_Start_2P({
  weight: "400",
  variable: "--font-arcade",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Little Research Lab",
  description: "Content publishing platform",
};

import { Toaster } from "@/components/ui/sonner"
import { ApiConfig } from "@/components/api-config"
import { ThemeProvider } from "@/components/providers/ThemeProvider"

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${sansFont.variable} ${monoFont.variable} ${arcadeFont.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <ApiConfig />
          <div className="min-h-screen">
            {children}
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
