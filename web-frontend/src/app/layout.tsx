import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { Sidebar } from "@/components/sidebar";
import { NotificationProvider } from "@/components/notification-provider";

export const metadata: Metadata = {
  title: "Mail Assistant",
  description: "AI 驱动的求职邮件智能分类助手",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap"
        />
      </head>
      <body className="min-h-full flex font-['JetBrains_Mono',monospace]">
        <NotificationProvider>
          <Sidebar />
          <main className="flex-1 overflow-hidden">{children}</main>
          <Toaster />
        </NotificationProvider>
      </body>
    </html>
  );
}
