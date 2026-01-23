import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

/**
 * NextAuth.js v5 configuration
 * Handles authentication with Google OAuth and syncs users to backend
 */
export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [
        Google({
            clientId: process.env.GOOGLE_CLIENT_ID || "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
        }),
    ],
    callbacks: {
        async jwt({ token, account, profile }) {
            // Persist the OAuth access_token and provider info to the token
            if (account) {
                token.accessToken = account.access_token;
                token.provider = account.provider;
                token.providerId = account.providerAccountId;
            }
            if (profile) {
                token.picture = profile.picture;
            }
            return token;
        },
        async session({ session, token }) {
            // Add custom properties to the session
            if (session.user) {
                session.user.id = token.sub || "";
                session.user.accessToken = token.accessToken as string;
                session.user.provider = token.provider as string;
                session.user.providerId = token.providerId as string;
            }
            return session;
        },
        async signIn({ user, account }) {
            // Sync user to backend database on sign in
            if (user && account) {
                try {
                    const backendUrl = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
                    const response = await fetch(`${backendUrl}/api/auth/sync-user`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            email: user.email,
                            name: user.name,
                            image: user.image,
                            provider: account.provider,
                            provider_id: account.providerAccountId,
                        }),
                    });

                    if (!response.ok) {
                        console.error("Failed to sync user to backend:", await response.text());
                    }
                } catch (error) {
                    console.error("Error syncing user to backend:", error);
                    // Don't block sign-in if backend sync fails
                }
            }
            return true;
        },
    },
    pages: {
        signIn: "/login",
        error: "/login",
    },
    session: {
        strategy: "jwt",
        maxAge: 30 * 24 * 60 * 60, // 30 days
    },
});

// Extend the Session type to include our custom properties
declare module "next-auth" {
    interface Session {
        user: {
            id: string;
            name?: string | null;
            email?: string | null;
            image?: string | null;
            accessToken?: string;
            provider?: string;
            providerId?: string;
        };
    }
}
