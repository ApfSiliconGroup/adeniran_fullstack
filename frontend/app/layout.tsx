import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adeniran Street Clinic",
  description: "Calm, secure clinic appointment management.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}