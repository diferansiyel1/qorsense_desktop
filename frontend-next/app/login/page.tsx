'use client';

/**
 * Login Page
 * 
 * Modern, corporate login interface for QorSense platform.
 * Features email/password authentication with loading states and error handling.
 */

import { useState, FormEvent, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Mail, Lock, AlertCircle, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const { login, isAuthenticated } = useAuth();

    // Hydration safety - wait for client mount
    const [mounted, setMounted] = useState(false);

    // Form state
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    // UI state
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Mount effect for hydration safety
    useEffect(() => {
        setMounted(true);
    }, []);

    // Redirect if already authenticated
    useEffect(() => {
        if (mounted && isAuthenticated) {
            router.push('/');
        }
    }, [mounted, isAuthenticated, router]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            await login({ email, password });
            // AuthContext handles redirect to /
        } catch (err: unknown) {
            console.error('[Login] Error:', err);

            // Extract error message
            let message = 'Giriş yapılırken bir hata oluştu';

            if (err instanceof Error) {
                if (err.message.includes('401') || err.message.toLowerCase().includes('unauthorized')) {
                    message = 'Email veya şifre hatalı';
                } else if (err.message.includes('403')) {
                    message = 'Hesabınız devre dışı bırakılmış';
                } else if (err.message.includes('Network') || err.message.includes('fetch')) {
                    message = 'Sunucuya bağlanılamıyor. Lütfen internet bağlantınızı kontrol edin.';
                } else {
                    message = err.message;
                }
            }

            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Only use isSubmitting for loading state (no authLoading to avoid hydration mismatch)
    const isLoading = isSubmitting;

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
            {/* Background decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl" />
            </div>

            <Card className="w-full max-w-md relative z-10 bg-slate-800/80 backdrop-blur-xl border-slate-700/50 shadow-2xl shadow-black/20">
                <CardHeader className="space-y-4 text-center pb-2">
                    {/* Logo */}
                    <div className="flex justify-center">
                        <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/25">
                            <div className="w-full h-full rounded-2xl bg-slate-800 flex items-center justify-center overflow-hidden">
                                <Image
                                    src="/logo.png"
                                    alt="QorSense Logo"
                                    width={64}
                                    height={64}
                                    className="object-contain"
                                    priority
                                />
                            </div>
                        </div>
                    </div>

                    <div className="space-y-1">
                        <CardTitle className="text-2xl font-bold text-white">
                            QorSense'e Hoş Geldiniz
                        </CardTitle>
                        <CardDescription className="text-slate-400">
                            Sensör izleme ve bakım platformu
                        </CardDescription>
                    </div>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-5 pt-4">
                        {/* Error Alert */}
                        {error && (
                            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm animate-in fade-in slide-in-from-top-1 duration-200">
                                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                <p>{error}</p>
                            </div>
                        )}

                        {/* Email Field */}
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-slate-300 text-sm font-medium">
                                Email Adresi
                            </Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="ornek@sirket.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10 h-12 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 focus:ring-blue-500/20 transition-all"
                                    required
                                    disabled={isLoading}
                                    autoComplete="email"
                                />
                            </div>
                        </div>

                        {/* Password Field */}
                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-slate-300 text-sm font-medium">
                                Şifre
                            </Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-10 pr-10 h-12 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 focus:ring-blue-500/20 transition-all"
                                    required
                                    disabled={isLoading}
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                                    tabIndex={-1}
                                >
                                    {showPassword ? (
                                        <EyeOff className="w-5 h-5" />
                                    ) : (
                                        <Eye className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Remember Me & Forgot Password */}
                        <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                    className="w-4 h-4 rounded border-slate-600 bg-slate-900/50 text-blue-500 focus:ring-blue-500/20 focus:ring-offset-0 cursor-pointer"
                                    disabled={isLoading}
                                />
                                <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
                                    Beni hatırla
                                </span>
                            </label>
                            <Link
                                href="/forgot-password"
                                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                            >
                                Şifremi unuttum
                            </Link>
                        </div>
                    </CardContent>

                    <CardFooter className="flex flex-col gap-4 pt-2">
                        {/* Submit Button */}
                        <Button
                            type="submit"
                            className="w-full h-12 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={isLoading || !email || !password}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                    Giriş yapılıyor...
                                </>
                            ) : (
                                'Giriş Yap'
                            )}
                        </Button>

                        {/* Register Link */}
                        <p className="text-sm text-slate-400 text-center">
                            Hesabınız yok mu?{' '}
                            <Link
                                href="/register"
                                className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                            >
                                Kayıt olun
                            </Link>
                        </p>
                    </CardFooter>
                </form>

                {/* Footer */}
                <div className="px-6 pb-6 pt-2">
                    <div className="pt-4 border-t border-slate-700/50">
                        <p className="text-xs text-slate-500 text-center">
                            © 2024 Pikolab. Tüm hakları saklıdır.
                        </p>
                    </div>
                </div>
            </Card>

            {/* Demo credentials hint (development only) */}
            {process.env.NODE_ENV === 'development' && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-slate-800/90 backdrop-blur border border-slate-700/50 rounded-lg px-4 py-2 text-xs text-slate-400 shadow-lg">
                    <span className="font-medium text-slate-300">Demo:</span>{' '}
                    admin@pikolab.com / admin123
                </div>
            )}
        </div>
    );
}
