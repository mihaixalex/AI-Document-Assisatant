import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Toaster } from "@/components/ui/toaster"
import { ConversationProvider } from "@/contexts/conversation-context"

import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "NEXUS - AI Document Assistant",
  description: "AI-powered document assistant with PDF chat capabilities",
  icons: {
    icon: '/icon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.className} h-screen overflow-hidden bg-black text-white`}>
        <ConversationProvider>
          <div className="flex h-screen bg-black text-white">
            {children}
          </div>
        </ConversationProvider>
        <Toaster />
      </body>
    </html>
  )
}
