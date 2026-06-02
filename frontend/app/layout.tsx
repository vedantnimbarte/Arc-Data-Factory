import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Nav } from "@/components/nav";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "ARC Data Factory",
  description: "Control dashboard for the ARC training-data pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Nav />
            <main className="flex-1 p-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
