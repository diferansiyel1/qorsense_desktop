'use client';

/**
 * Register Page
 * 
 * User registration interface for QorSense platform.
 * Creates both a new Organization and an Admin User.
 */

import { useState, FormEvent, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Mail, Lock, User as UserIcon, AlertCircle, Eye, EyeOff, CheckCircle, Building2 } from 'lucide-react';

export default function RegisterPage() {
    const router = useRouter();
    const { login, isAuthenticated } = useAuth();

    // Hydration safety
    const [mounted, setMounted] = useState(false);

    // Form state
    const [organizationName, setOrganizationName] = useState('');
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    // UI state
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

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
            // 1. Register (Creates Org + Admin)
            await authApi.register({
                organization_name: organizationName,
                full_name: fullName,
                email,
                password,
            });

            setSuccess(true);

            // 2. Auto Login
            try {
                await login({ email, password });
                // AuthContext handles redirect to /
            } catch (loginErr) {
                console.warn('Auto-login failed after registration:', loginErr);
                // If auto-login fails, redirect to login page after a delay
                setTimeout(() => {
                    router.push('/login');
                }, 2000);
            }

        } catch (err: any) {
            console.error('[Register] Error:', err);

            let message = 'Kayıt işlemi başarısız oldu';
            if (err.message && err.message.includes('400')) {
                message = 'Geçersiz bilgi. Email veya kurum adı kullanımda olabilir.';
            } else if (err.data?.detail) {
                message = typeof err.data.detail === 'string' ? err.data.detail : 'Geçersiz bilgiler';
            } else {
                message = err.message || 'Sunucu hatası';
            }

            setError(message);
            setIsSubmitting(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
                <Card className="w-full max-w-md bg-slate-800/80 backdrop-blur-xl border-slate-700/50 shadow-2xl">
                    <CardContent className="pt-6 flex flex-col items-center text-center space-y-4">
                        <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-2">
                            <CheckCircle className="w-8 h-8 text-green-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">Hesap Oluşturuldu!</h2>
                        <p className="text-slate-400">
                            Kurumunuz ve yönetici hesabınız hazır. Sisteme giriş yapılıyor...
                        </p>
                        <Loader2 className="w-6 h-6 text-blue-500 animate-spin mt-4" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    const isLoading = isSubmitting;

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
            {/* Background decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
            </div>

            <Card className="w-full max-w-md relative z-10 bg-slate-800/80 backdrop-blur-xl border-slate-700/50 shadow-2xl shadow-black/20">
                <CardHeader className="space-y-4 text-center pb-2">
                    <div className="flex justify-center">
                        <div className="relative w-16 h-16">
                            <Image
                                src="/logo.png"
                                alt="QorSense Logo"
                                width={64}
                                height={64}
                                className="object-contain"
                            />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <CardTitle className="text-2xl font-bold text-white">
                            Hesap Oluşturun
                        </CardTitle>
                        <CardDescription className="text-slate-400">
                            Organizasyon ve yönetici hesabı oluşturun
                        </CardDescription>
                    </div>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4 pt-2">
                        {error && (
                            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm animate-in fade-in slide-in-from-top-1 duration-200">
                                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                <p>{error}</p>
                            </div>
                        )}

                        {/* Organization Name */}
                        <div className="space-y-2">
                            <Label htmlFor="orgName" className="text-slate-300 text-sm font-medium">Kurum Adı</Label>
                            <div className="relative">
                                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="orgName"
                                    type="text"
                                    placeholder="Şirket veya Kurum Adı"
                                    value={organizationName}
                                    onChange={(e) => setOrganizationName(e.target.value)}
                                    className="pl-10 h-10 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 transition-all"
                                    required
                                    disabled={isLoading}
                                    minLength={2}
                                />
                            </div>
                        </div>

                        {/* Full Name */}
                        <div className="space-y-2">
                            <Label htmlFor="fullname" className="text-slate-300 text-sm font-medium">Yönetici Adı Soyadı</Label>
                            <div className="relative">
                                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="fullname"
                                    type="text"
                                    placeholder="Ad Soyad"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    className="pl-10 h-10 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 transition-all"
                                    required
                                    disabled={isLoading}
                                    minLength={2}
                                />
                            </div>
                        </div>

                        {/* Email */}
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-slate-300 text-sm font-medium">Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="ornek@sirket.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10 h-10 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 transition-all"
                                    required
                                    disabled={isLoading}
                                    autoComplete="email"
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-2">
                            <Label htmlFor="password" className="text-slate-300 text-sm font-medium">Şifre</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="•••••••• (en az 8 karakter)"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-10 pr-10 h-10 bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-blue-500 transition-all"
                                    required
                                    disabled={isLoading}
                                    minLength={8}
                                    autoComplete="new-password"
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
                    </CardContent>

                    <CardFooter className="flex flex-col gap-4 pt-2">
                        <Button
                            type="submit"
                            className="w-full h-11 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold shadow-lg shadow-blue-500/25 transition-all duration-200 disabled:opacity-50"
                            disabled={isLoading || !email || !password || !organizationName || !fullName}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                    Hesap oluşturuluyor...
                                </>
                            ) : (
                                'Hesap Oluştur'
                            )}
                        </Button>

                        <p className="text-sm text-slate-400 text-center">
                            Zaten hesabınız var mı?{' '}
                            <Link
                                href="/login"
                                className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                            >
                                Giriş yap
                            </Link>
                        </p>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
