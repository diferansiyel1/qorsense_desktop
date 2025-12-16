import type { NextConfig } from "next";

/**
 * Next.js Configuration for Electron Desktop App
 * 
 * Key settings for Electron compatibility:
 * 1. output: "export" - Static HTML export, no Node.js runtime needed
 * 2. images.unoptimized - Disable Next.js image optimization (not available in static export)
 * 3. trailingSlash - Disabled for cleaner file:// protocol URLs
 */
const nextConfig: NextConfig = {
  // Static export mode - generates pure HTML/JS/CSS
  // Required for Electron file:// protocol
  output: "export",

  // Disable Next.js Image Optimization
  // Required for static export and Electron file:// protocol
  images: {
    unoptimized: true,
  },

  // Don't add trailing slashes to URLs
  // Better for Electron's file:// protocol
  trailingSlash: false,

  // Disable server-side features for pure client-side rendering
  // This ensures all pages work in Electron
  experimental: {
    // Disable middleware (not available in static export)
  },
};

export default nextConfig;
