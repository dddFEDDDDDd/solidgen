import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Solidgen",
  description: "Image to 3D generation platform (TRELLIS.2)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-50">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <header className="mb-10 flex items-center justify-between">
            <a href="/" className="text-xl font-semibold tracking-tight">
              Solidgen
            </a>
            <nav className="flex gap-4 text-sm text-zinc-300">
              <a className="hover:text-white" href="/dashboard">
                Dashboard
              </a>
              <a className="hover:text-white" href="/billing">
                Billing
              </a>
              <a className="hover:text-white" href="/login">
                Login
              </a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}


