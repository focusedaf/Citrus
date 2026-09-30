import type { Metadata } from "next";

import { Space_Grotesk, JetBrains_Mono } from "next/font/google";

import "./globals.css";

import { AppSidebar } from "@/components/app-sidebar";

import { SiteHeader } from "@/components/site-header";

import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar";

import { Toaster } from "@/components/ui/sonner";

import { StoreProvider } from "@/lib/store";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Citrus",
  description: "typeshit",
};

export default function RootLayout({
  children,
}: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`
        dark
        ${spaceGrotesk.variable}
        ${jetBrainsMono.variable}
        h-full
        antialiased
      `}
    >
      <body className="min-h-full flex flex-col">
        <StoreProvider>
          <SidebarProvider
            style={
              {
                "--sidebar-width": "calc(var(--spacing) * 68)",
                "--header-height": "calc(var(--spacing) * 12)",
              } as React.CSSProperties
            }
          >
            <AppSidebar variant="inset" />

            <SidebarInset>
              <SiteHeader />

              <div className="@container/main flex flex-1 flex-col gap-4 p-4 lg:p-6">
                {children}
              </div>
            </SidebarInset>
          </SidebarProvider>

          <Toaster theme="dark" />
        </StoreProvider>
      </body>
    </html>
  );
}