'use client';

import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import { User } from '@/types/api';

export default function ProfilePage() {
    const { user, loading: authLoading } = useAuth();
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);

    // Profile Form State
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');

    // Password Form State
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    useEffect(() => {
        if (user) {
            setFullName(user.full_name || '');
            setEmail(user.email || '');
        }
    }, [user]);

    const getInitials = (name: string | null) => {
        if (!name) return 'U';
        return name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase()
            .substring(0, 2);
    };

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            await api.auth.updateProfile({ full_name: fullName });
            toast({
                title: "Profile updated",
                description: "Your profile information has been updated successfully.",
            });
        } catch (error: any) {
            toast({
                variant: "destructive",
                title: "Update failed",
                description: error.message || "Could not update profile.",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();

        if (newPassword !== confirmPassword) {
            toast({
                variant: "destructive",
                title: "Passwords do not match",
                description: "New password and confirmation must match.",
            });
            return;
        }

        setIsLoading(true);
        try {
            await api.auth.changePassword({
                current_password: currentPassword,
                new_password: newPassword
            });
            toast({
                title: "Password changed",
                description: "Your password has been updated successfully.",
            });
            // Reset form
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (error: any) {
            toast({
                variant: "destructive",
                title: "Change failed",
                description: error.message || "Could not change password.",
            });
        } finally {
            setIsLoading(false);
        }
    };

    if (authLoading) {
        return (
            <div className="container mx-auto p-6 space-y-6">
                <div className="flex flex-col md:flex-row gap-6">
                    <div className="w-full md:w-1/3">
                        <Skeleton className="h-[300px] w-full rounded-xl" />
                    </div>
                    <div className="w-full md:w-2/3">
                        <Skeleton className="h-[400px] w-full rounded-xl" />
                    </div>
                </div>
            </div>
        );
    }

    if (!user) return null;

    return (
        <div className="container mx-auto p-6 space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left Column: Summary Card */}
                <Card className="md:col-span-1">
                    <CardHeader className="flex flex-col items-center text-center">
                        <Avatar className="h-24 w-24 mb-4">
                            <AvatarImage src="" />
                            <AvatarFallback className="text-2xl bg-primary/10 text-primary">
                                {getInitials(user.full_name)}
                            </AvatarFallback>
                        </Avatar>
                        <CardTitle className="text-xl">{user.full_name || 'User'}</CardTitle>
                        <CardDescription>{user.email}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-between items-center py-2 border-b">
                            <span className="text-sm font-medium">Role</span>
                            <Badge variant="outline" className="capitalize">
                                {user.role.replace('_', ' ')}
                            </Badge>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b">
                            <span className="text-sm font-medium">Organization</span>
                            <span className="text-sm text-muted-foreground">
                                {user.organization_id || 'N/A'}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-sm font-medium">Member Since</span>
                            <span className="text-sm text-muted-foreground">
                                {new Date(user.created_at).toLocaleDateString()}
                            </span>
                        </div>
                    </CardContent>
                </Card>

                {/* Right Column: Actions */}
                <div className="md:col-span-2">
                    <Tabs defaultValue="profile" className="w-full">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="profile">Profile Settings</TabsTrigger>
                            <TabsTrigger value="security">Security</TabsTrigger>
                        </TabsList>

                        {/* Tab 1: Profile Settings */}
                        <TabsContent value="profile">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Profile Information</CardTitle>
                                    <CardDescription>
                                        Update your public profile details.
                                    </CardDescription>
                                </CardHeader>
                                <form onSubmit={handleUpdateProfile}>
                                    <CardContent className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="fullName">Full Name</Label>
                                            <Input
                                                id="fullName"
                                                value={fullName}
                                                onChange={(e) => setFullName(e.target.value)}
                                                placeholder="John Doe"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="email">Email</Label>
                                            <Input
                                                id="email"
                                                value={email}
                                                disabled
                                                className="bg-muted"
                                            />
                                            <p className="text-xs text-muted-foreground">
                                                Email address cannot be changed.
                                            </p>
                                        </div>
                                    </CardContent>
                                    <CardFooter>
                                        <Button type="submit" disabled={isLoading}>
                                            {isLoading ? "Saving..." : "Save Changes"}
                                        </Button>
                                    </CardFooter>
                                </form>
                            </Card>
                        </TabsContent>

                        {/* Tab 2: Security */}
                        <TabsContent value="security">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Password</CardTitle>
                                    <CardDescription>
                                        Change your password. Ensure it is strong and secure.
                                    </CardDescription>
                                </CardHeader>
                                <form onSubmit={handleChangePassword}>
                                    <CardContent className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="currentPassword">Current Password</Label>
                                            <Input
                                                id="currentPassword"
                                                type="password"
                                                value={currentPassword}
                                                onChange={(e) => setCurrentPassword(e.target.value)}
                                                required
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="newPassword">New Password</Label>
                                            <Input
                                                id="newPassword"
                                                type="password"
                                                value={newPassword}
                                                onChange={(e) => setNewPassword(e.target.value)}
                                                required
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="confirmPassword">Confirm New Password</Label>
                                            <Input
                                                id="confirmPassword"
                                                type="password"
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                required
                                            />
                                        </div>
                                    </CardContent>
                                    <CardFooter>
                                        <Button type="submit" disabled={isLoading}>
                                            {isLoading ? "Updating..." : "Change Password"}
                                        </Button>
                                    </CardFooter>
                                </form>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}
