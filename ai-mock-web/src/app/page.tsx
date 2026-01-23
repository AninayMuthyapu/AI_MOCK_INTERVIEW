"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Moon, Sun, Zap, Award, Shield } from "lucide-react"
import { useTheme } from "next-themes"

export default function Home() {
  const [mounted, setMounted] = useState(false)
  const { theme, setTheme } = useTheme()
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [trails, setTrails] = useState<Array<{ x: number; y: number; id: number }>>([])
  const isDark = theme === 'dark'

  // Handle mouse movement for liquid cursor effect
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
      const newTrail = { x: e.clientX, y: e.clientY, id: Date.now() }
      setTrails((prev) => [...prev.slice(-8), newTrail])
    }

    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [])

  // Ensure component is mounted to avoid hydration issues .
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  const toggleTheme = () => {
    setTheme(isDark ? 'light' : 'dark')
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Liquid cursor effect */}
      <div
        className="fixed w-8 h-8 bg-primary/20 rounded-full pointer-events-none z-50 transform -translate-x-1/2 -translate-y-1/2 transition-transform duration-100"
        style={{
          left: `${mousePosition.x}px`,
          top: `${mousePosition.y}px`,
          boxShadow: '0 0 30px 10px rgba(59, 130, 246, 0.3)'
        }}
      />
      {trails.map((trail, index) => (
        <div
          key={trail.id}
          className="fixed w-6 h-6 bg-primary/10 rounded-full pointer-events-none z-40 transform -translate-x-1/2 -translate-y-1/2 transition-all duration-300"
          style={{
            left: `${trail.x}px`,
            top: `${trail.y}px`,
            opacity: (index + 1) / trails.length * 0.6,
            transform: `translate(-50%, -50%) scale(${(index + 1) / trails.length})`,
          }}
        />
      ))}

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center transition-transform group-hover:scale-110">
              <span className="text-primary-foreground font-bold text-xl">H</span>
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-primary via-accent to-secondary bg-clip-text text-transparent">
              HackInterview
            </span>
          </Link>

          <div className="flex items-center space-x-6">
            <Link href="#features" className="text-foreground/80 hover:text-primary transition-colors">
              Features
            </Link>
            <Link href="#testimonials" className="text-foreground/80 hover:text-primary transition-colors">
              Testimonials
            </Link>
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full hover:bg-accent/20 transition-colors"
              aria-label="Toggle theme"
            >
              {isDark ? (
                <Sun className="w-5 h-5 text-foreground/80" />
              ) : (
                <Moon className="w-5 h-5 text-foreground/80" />
              )}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="pt-32 pb-20 px-6 max-w-7xl mx-auto relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary via-accent to-secondary mb-6">
            AI-Powered Mock Interviews
          </h1>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            Practice with realistic interview rounds, AI-generated questions, and instant feedback to land your dream job.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              href="/login?callbackUrl=%2Fresume"
              className="px-8 py-3.5 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 transition-colors shadow-lg hover:shadow-primary/30"
            >
              Start Free Trial
            </Link>
            <Link
              href="#features"
              className="px-8 py-3.5 border border-border bg-card hover:bg-accent/20 text-foreground font-medium rounded-lg transition-colors"
            >
              Learn More
            </Link>
          </div>
        </div>
      </div>

      {/* Floating background elements */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-primary/10 blur-3xl animate-float" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full bg-accent/10 blur-3xl animate-float animation-delay-2000" />
        <div className="absolute top-1/3 right-1/3 w-40 h-40 rounded-full bg-secondary/10 blur-3xl animate-float animation-delay-4000" />
      </div>

      {/* Features Section */}
      <section id="features" className="py-20 px-6 max-w-7xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent mb-4">
            Why Choose HackInterview?
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Our platform offers everything you need to ace your next technical interview.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-card p-8 rounded-xl border border-border hover:border-primary/30 transition-colors">
            <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-3">AI-Powered Practice</h3>
            <p className="text-muted-foreground">
              Get realistic interview questions generated by advanced AI, tailored to your target role and experience level.
            </p>
          </div>

          <div className="bg-card p-8 rounded-xl border border-border hover:border-primary/30 transition-colors">
            <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
              <Award className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Instant Feedback</h3>
            <p className="text-muted-foreground">
              Receive detailed feedback on your answers, including areas for improvement and suggested responses.
            </p>
          </div>

          <div className="bg-card p-8 rounded-xl border border-border hover:border-primary/30 transition-colors">
            <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Secure & Private</h3>
            <p className="text-muted-foreground">
              Your data is encrypted and never shared. Practice with confidence knowing your information is secure.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6 bg-gradient-to-br from-card to-card/50 relative overflow-hidden">
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to ace your next interview?</h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join thousands of developers who have landed their dream jobs with our interview preparation platform.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              href="/login?callbackUrl=%2Fresume"
              className="px-8 py-3.5 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 transition-colors shadow-lg hover:shadow-primary/30"
            >
              Start Free Trial
            </Link>
            <Link
              href="#features"
              className="px-8 py-3.5 border border-border bg-card hover:bg-accent/20 text-foreground font-medium rounded-lg transition-colors"
            >
              Learn More
            </Link>
          </div>
        </div>
        <div className="absolute inset-0 -z-10 opacity-10">
          <div className="absolute inset-0 bg-grid-pattern" />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-3 mb-6 md:mb-0">
              <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-xl">H</span>
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-primary via-accent to-secondary bg-clip-text text-transparent">
                HackInterview
              </span>
            </div>
            <div className="flex space-x-6">
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                Privacy
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                Contact
              </Link>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-border/20 text-center text-sm text-muted-foreground">
            © {new Date().getFullYear()} HackInterview. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
