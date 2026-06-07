import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Novel-to-Script Pro - AI驱动的改编管线",
  description:
    "使用AI Agent将小说转化为专业剧本。六阶段管线，覆盖从原文导入到电影级分镜的完整流程。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className="h-full antialiased"
    >
      <body className="min-h-full bg-[var(--surface)] text-[var(--text-primary)]">
        <div className="grain-overlay" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
