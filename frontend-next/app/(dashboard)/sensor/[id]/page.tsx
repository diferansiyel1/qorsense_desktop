import SensorClient from './SensorClient';

// Required for static export - pre-generate common sensor ID paths
// In Electron app, additional sensors will still work via client-side routing
export async function generateStaticParams() {
    // Generate paths for common sensor IDs (1-100)
    // This covers most use cases for SCADA systems
    return Array.from({ length: 100 }, (_, i) => ({
        id: String(i + 1),
    }));
}

// Server component wrapper - passes ID to client component
export default async function SensorDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <SensorClient sensorId={id} />;
}
