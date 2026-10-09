import type { Metadata } from "next";
import { Cormorant_Garamond, Jost } from "next/font/google";
import "./globals.css";
import { DemoProvider } from "@/components/demo-provider";

const cormorant = Cormorant_Garamond({ subsets: ["latin"], variable: "--font-cormorant", weight: ["300", "400", "500", "600"], style: ["normal", "italic"] });
const jost = Jost({ subsets: ["latin"], variable: "--font-jost", weight: ["300", "400", "500", "600"] });

export const metadata: Metadata = {
  title: "IWP AI Wedding Concierge — Concept Demo",
  description: "An independent concept demonstration of an AI wedding concierge and team workspace."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${cormorant.variable} ${jost.variable} font-sans antialiased`}>
        <DemoProvider>{children}</DemoProvider>
      </body>
    </html>
  );
}
