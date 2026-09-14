import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-plus-jakarta",
  fallback: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
});

export const metadata: Metadata = {
  title: {
    default: "Adeniran Street Clinic",
    template: "%s · Adeniran Street Clinic",
  },
  description:
    "Book appointments, read your consultation notes and run the clinic diary. Adeniran Street Clinic's booking service for patients, doctors and front desk staff.",
  applicationName: "Adeniran Street Clinic",
  keywords: [
    "clinic",
    "appointments",
    "booking",
    "consultation notes",
    "healthcare",
  ],
  authors: [{ name: "Team 3 - Group Silicon" }],
  openGraph: {
    title: "Adeniran Street Clinic",
    description:
      "One calm place to book care, read your notes and run the clinic diary.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7fcfb" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1f1e" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-theme="clinic"
      className={plusJakarta.variable}
      suppressHydrationWarning
    >
      <body className="min-h-dvh">
        <a
          href="#main"
          className="btn btn-primary btn-sm sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-100"
        >
          Skip to main content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
