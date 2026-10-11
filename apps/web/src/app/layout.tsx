import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import TopNav from "@/components/TopNav";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/components/Toast";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CampusCue",
  description: "CampusCue Next.js App",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-screen flex flex-col bg-[#F5EEE9] text-gray-900 font-sans">
        <AuthProvider><ToastProvider>
        <TopNav />
        <main className="flex-1 pt-16">
          {children}
        </main>
        </ToastProvider></AuthProvider>
      </body>
    </html>
  );
}
