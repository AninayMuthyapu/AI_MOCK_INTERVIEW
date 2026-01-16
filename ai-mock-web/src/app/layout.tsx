import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { VoiceProvider } from "@/contexts/VoiceContext";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "sonner";
import SimpleParticles from "@/components/SimpleParticles";
import TokenUsage from "@/components/TokenUsage";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HackInterview - AI-Powered Mock Interviews",
  description: "Practice with AI-powered mock interviews and get instant feedback to land your dream job.",
  keywords: ["interview preparation", "mock interview", "AI interview", "coding interview", "technical interview"],
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <VoiceProvider>
            <main className="min-h-screen relative overflow-hidden bg-background">
              {/* Background Elements */}
              <div className="fixed inset-0 -z-10 overflow-hidden">
                {/* Base Background */}
                <div className="absolute inset-0 bg-background -z-30"></div>

                {/* Subtle Grid at the very back */}
                <div className="absolute inset-0 bg-grid opacity-20 dark:opacity-10 -z-20"></div>

                {/* Gradient Overlay below particles */}
                <div className="absolute inset-0 bg-gradient-to-br from-background/80 via-background/50 to-background/80 -z-10 pointer-events-none"></div>
              </div>

              {/* Particle System ABOVE overlays, BELOW content */}
              <SimpleParticles />

              {/* Page Content */}
              <div className="relative z-30">
                {children}
              </div>
            </main>
            <Toaster position="top-center" richColors />
            <TokenUsage />
          </VoiceProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
