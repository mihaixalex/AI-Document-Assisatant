import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Toaster } from "@/components/ui/toaster"
import { ThemeProvider } from "next-themes"
import { ConversationProvider } from "@/contexts/conversation-context"
import { SidebarProvider } from "@/components/ui/sidebar"

import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Learning LangChain Book Chatbot Demo",
  description: "A chatbot demo based on Learning LangChain (O'Reilly)",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          <ConversationProvider>
            <SidebarProvider>
              {children}
            </SidebarProvider>
          </ConversationProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}