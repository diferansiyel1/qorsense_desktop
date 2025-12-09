/**
 * Login Page Layout
 * 
 * Minimal layout without sidebar for the login page.
 * Auth pages should display without the main navigation.
 */

import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Giriş Yap - QorSense',
    description: 'QorSense platformuna giriş yapın',
};

export default function LoginLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    // Return children directly without sidebar wrapper
    // The main layout's AuthProvider still wraps this
    return (
        <div className="fixed inset-0 bg-slate-900">
            {children}
        </div>
    );
}
