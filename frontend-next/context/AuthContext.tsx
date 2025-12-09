'use client';

/**
 * Authentication Context
 * 
 * Provides global auth state management for the application.
 * Handles token storage in both localStorage and cookies for SSR compatibility.
 * 
 * @module context/AuthContext
 */

import React, {
    createContext,
    useContext,
    useState,
    useEffect,
    useCallback,
    ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import type { User, TokenResponse, LoginRequest } from '@/types/api';
import { authApi, tokenStorage } from '@/lib/api';

// ==============================================================================
// CONSTANTS
// ==============================================================================

const AUTH_COOKIE_NAME = 'auth_token';
const COOKIE_OPTIONS: Cookies.CookieAttributes = {
    expires: 7, // 7 days
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
};

// ==============================================================================
// TYPES
// ==============================================================================

interface AuthContextType {
    /** Current authenticated user, null if not logged in */
    user: User | null;
    /** True while checking auth status on initial load */
    loading: boolean;
    /** True if user is authenticated */
    isAuthenticated: boolean;
    /** Login with email and password */
    login: (credentials: LoginRequest) => Promise<void>;
    /** Logout and clear all tokens */
    logout: () => void;
    /** Refresh user data from the server */
    refreshUser: () => Promise<void>;
}

interface AuthProviderProps {
    children: ReactNode;
}

// ==============================================================================
// CONTEXT
// ==============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ==============================================================================
// PROVIDER COMPONENT
// ==============================================================================

export function AuthProvider({ children }: AuthProviderProps) {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    /**
     * Store token in both localStorage and cookies.
     * localStorage for client-side access, cookies for SSR/middleware.
     */
    const storeTokens = useCallback((tokens: TokenResponse) => {
        // Store in localStorage via tokenStorage utility
        tokenStorage.setTokens(tokens);

        // Also store in cookies for SSR compatibility
        Cookies.set(AUTH_COOKIE_NAME, tokens.access_token, COOKIE_OPTIONS);
    }, []);

    /**
     * Clear all stored tokens and cookies.
     */
    const clearTokens = useCallback(() => {
        // Clear localStorage
        tokenStorage.clearTokens();

        // Clear cookies
        Cookies.remove(AUTH_COOKIE_NAME);
    }, []);

    /**
     * Fetch current user from the /me endpoint.
     */
    const fetchUser = useCallback(async (): Promise<User | null> => {
        try {
            const userData = await authApi.getMe();
            return userData;
        } catch (error) {
            console.warn('[AuthContext] Failed to fetch user:', error);
            return null;
        }
    }, []);

    /**
     * Refresh user data from the server.
     */
    const refreshUser = useCallback(async () => {
        const userData = await fetchUser();
        setUser(userData);
    }, [fetchUser]);

    /**
     * Login with email and password.
     * Stores tokens and fetches user data.
     */
    const login = useCallback(async (credentials: LoginRequest) => {
        setLoading(true);
        try {
            // Call login API - this stores tokens in localStorage via tokenStorage
            const tokens = await authApi.login(credentials);

            // Also store in cookies for SSR
            Cookies.set(AUTH_COOKIE_NAME, tokens.access_token, COOKIE_OPTIONS);

            // Fetch user data
            const userData = await fetchUser();
            setUser(userData);

            // Redirect to dashboard
            router.push('/');
        } catch (error) {
            // Clear any partial state
            clearTokens();
            setUser(null);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchUser, clearTokens, router]);

    /**
     * Logout user and redirect to login page.
     */
    const logout = useCallback(() => {
        // Clear all tokens
        clearTokens();

        // Clear user state
        setUser(null);

        // Call backend logout (fire and forget)
        authApi.logout();

        // Redirect to login
        router.push('/login');
    }, [clearTokens, router]);

    /**
     * Check for existing auth on mount.
     * If token exists in cookie, try to fetch user data.
     */
    useEffect(() => {
        const initAuth = async () => {
            setLoading(true);

            try {
                // Check for token in cookie first (SSR compatible)
                const cookieToken = Cookies.get(AUTH_COOKIE_NAME);
                const localToken = tokenStorage.getAccessToken();

                // If we have a token somewhere
                if (cookieToken || localToken) {
                    // Sync tokens if needed
                    if (cookieToken && !localToken) {
                        // Cookie has token but localStorage doesn't - restore
                        localStorage.setItem('qorsense_access_token', cookieToken);
                    } else if (localToken && !cookieToken) {
                        // localStorage has token but cookie doesn't - restore
                        Cookies.set(AUTH_COOKIE_NAME, localToken, COOKIE_OPTIONS);
                    }

                    // Try to fetch user data to validate token
                    const userData = await fetchUser();

                    if (userData) {
                        setUser(userData);
                    } else {
                        // Token is invalid, clear everything
                        clearTokens();
                        setUser(null);
                    }
                } else {
                    // No token found
                    setUser(null);
                }
            } catch (error) {
                console.error('[AuthContext] Init auth error:', error);
                clearTokens();
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        initAuth();
    }, [fetchUser, clearTokens]);

    // ==============================================================================
    // CONTEXT VALUE
    // ==============================================================================

    const contextValue: AuthContextType = {
        user,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
    };

    return (
        <AuthContext.Provider value={contextValue}>
            {children}
        </AuthContext.Provider>
    );
}

// ==============================================================================
// HOOK
// ==============================================================================

/**
 * Hook to access auth context.
 * Must be used within an AuthProvider.
 */
export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);

    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    return context;
}

// ==============================================================================
// UTILITY EXPORTS
// ==============================================================================

export { AUTH_COOKIE_NAME };
