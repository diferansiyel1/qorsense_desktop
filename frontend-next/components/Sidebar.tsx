"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Activity,
    CalendarClock,
    Database,
    FlaskConical,
    FileText,
    Settings,
    LogOut,
    User as UserIcon,
    MoreVertical
} from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/context/AuthContext";

// Separator Component
const Separator = ({ title }: { title?: string }) => (
    <div className="px-3 py-2 mt-4 mb-1">
        {title ? (
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title}</h3>
        ) : (
            <div className="h-px bg-slate-gray/30" />
        )}
    </div>
);

const navGroups = [
    {
        title: "Platform",
        items: [
            {
                title: "Dashboard",
                href: "/",
                icon: LayoutDashboard,
            },
            {
                title: "Sensors",
                href: "/sensor-analysis", // Kept original link, renamed title to Sensors per logic
                icon: Activity,
            },
        ]
    },
    {
        title: "Operations",
        items: [
            {
                title: "Maintenance",
                href: "/maintenance",
                icon: CalendarClock,
            },
            {
                title: "Data Sources",
                href: "/data-sources",
                icon: Database,
            },
            {
                title: "Simulation Lab",
                href: "/simulation",
                icon: FlaskConical,
            },
        ]
    },
    {
        title: "Management",
        items: [
            {
                title: "Reports Archive",
                href: "/reports",
                icon: FileText,
            },
            {
                title: "Settings",
                href: "/settings",
                icon: Settings,
            },
        ]
    }
];

export function Sidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    return (
        <aside className="flex w-64 flex-col bg-[#111a22] p-4 text-white h-screen fixed left-0 top-0 border-r border-slate-gray/50 overflow-y-auto">
            <div className="flex-grow">
                {/* Brand / Logo Section */}
                <div className="flex items-center justify-center py-6 mb-2">
                    <div className="relative w-48 h-20">
                        <Image
                            src="/logo.png"
                            alt="QorSense Logo"
                            fill
                            className="object-contain"
                            priority
                        />
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex flex-col gap-1">
                    {navGroups.map((group, groupIndex) => (
                        <div key={groupIndex}>
                            {/* Logic for separators: Show separator between groups, or logic based on index */}
                            {groupIndex > 0 && <Separator title={group.title} />}

                            {groupIndex === 0 && <div className="mb-2" />}


                            {group.items.map((item) => {
                                const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={cn(
                                            "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative overflow-hidden",
                                            isActive
                                                ? "bg-slate-gray/20 text-[#00ADB5] shadow-[0_0_15px_-3px_rgba(0,173,181,0.3)] border border-[#00ADB5]/20"
                                                : "hover:bg-slate-gray/30 text-gray-400 hover:text-white"
                                        )}
                                    >
                                        {/* Glow effect helper for active state */}
                                        {isActive && (
                                            <div className="absolute inset-0 bg-[#00ADB5]/5 pointer-events-none" />
                                        )}

                                        <item.icon
                                            className={cn(
                                                "w-5 h-5 transition-colors relative z-10",
                                                isActive ? "text-[#00ADB5] drop-shadow-[0_0_8px_rgba(0,173,181,0.5)]" : "text-gray-400 group-hover:text-white"
                                            )}
                                        />
                                        <p className={cn(
                                            "text-sm font-medium leading-normal transition-colors relative z-10",
                                            isActive ? "text-[#00ADB5]" : "text-gray-400 group-hover:text-white"
                                        )}>
                                            {item.title}
                                        </p>
                                    </Link>
                                );
                            })}
                        </div>
                    ))}
                </nav>
            </div>

            {/* User Footer */}
            <div className="border-t border-slate-gray/50 pt-4 mt-4 bg-[#111a22]">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button className="flex items-center gap-3 px-2 py-2 w-full rounded-lg hover:bg-slate-gray/50 transition-colors cursor-pointer text-left outline-none group">
                            <Avatar className="h-10 w-10 border-2 border-slate-gray transition-colors group-hover:border-[#00ADB5]">
                                <AvatarImage src="" />
                                <AvatarFallback className="bg-slate-gray text-white font-medium">
                                    {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex flex-col flex-1 min-w-0">
                                <h1 className="text-white text-sm font-semibold leading-normal truncate">
                                    {user?.full_name || 'User'}
                                </h1>
                                <p className="text-[#92adc9] text-xs font-medium leading-normal truncate capitalize">
                                    {user?.role?.replace('_', ' ') || 'Guest'}
                                </p>
                            </div>
                            <MoreVertical className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-56" align="end" side="right" sideOffset={10}>
                        <DropdownMenuLabel>My Account</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <Link href="/profile">
                            <DropdownMenuItem className="cursor-pointer">
                                <UserIcon className="mr-2 h-4 w-4" />
                                <span>Profile</span>
                            </DropdownMenuItem>
                        </Link>
                        <Link href="/settings">
                            <DropdownMenuItem className="cursor-pointer">
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Settings</span>
                            </DropdownMenuItem>
                        </Link>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="cursor-pointer text-red-500 hover:text-red-500 focus:text-red-500" onClick={logout}>
                            <LogOut className="mr-2 h-4 w-4" />
                            <span>Log out</span>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </aside>
    );
}
