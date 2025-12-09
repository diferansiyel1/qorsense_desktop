"use client";

import { useState, useEffect } from 'react';
import { SmartSensorCard } from "@/components/SmartSensorCard";
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, ShieldAlert, Microscope } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { api, Sensor } from "@/lib/api";
import { AddSensorModal } from "@/components/AddSensorModal";

export default function Dashboard() {
    const [sensors, setSensors] = useState<any[]>([]); // Using any to mix Sensor + UI props
    const [loading, setLoading] = useState(true);

    const fetchSensors = async () => {
        setLoading(true);
        try {
            const response = await api.getSensors();
            const sensorsData = (response as any).items ? (response as any).items : response;

            const mapped = Array.isArray(sensorsData) ? sensorsData.map((s: any) => {
                // Normalization Logic
                let rawStatus = (s.latest_status || 'Unknown').trim().toUpperCase();
                let finalStatus = 'Unknown';

                // Map various inputs to standard Enum
                if (['NORMAL', 'GREEN', 'GOOD', 'OK'].includes(rawStatus)) finalStatus = 'Normal';
                else if (['WARNING', 'YELLOW', 'WARN'].includes(rawStatus)) finalStatus = 'Warning';
                else if (['CRITICAL', 'RED', 'BAD', 'FAIL'].includes(rawStatus)) finalStatus = 'Critical';
                else {
                    // Fallback to score if status is unrecognized/Unknown
                    const score = s.latest_health_score ?? 0;
                    if (score > 80) finalStatus = 'Normal';
                    else if (score >= 50) finalStatus = 'Warning';
                    else finalStatus = 'Critical';
                }

                const score = s.latest_health_score ?? 0;

                return {
                    id: s.id,
                    name: s.name,
                    location: s.location,
                    healthScore: score,
                    status: finalStatus as 'Normal' | 'Warning' | 'Critical' | 'Unknown',
                    type: s.source_type
                };
            }) : [];
            setSensors(mapped);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSensors();
    }, []);

    const handleSensorCreated = (newSensor: Sensor) => {
        // Optimistic update or refetch
        fetchSensors();
    };

    const criticalCount = sensors.filter(s => s.status === 'Critical').length;
    const warningCount = sensors.filter(s => s.status === 'Warning').length;

    return (
        <div className="min-h-screen bg-background p-6 md:p-8">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                            <Microscope className="w-8 h-8 text-primary" />
                            Sensor Monitoring
                        </h1>
                        <p className="text-muted-foreground mt-1">Real-time analysis for pH, DO, Flow & Pressure instrumentation.</p>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Global Status Pill */}
                        <div className="hidden md:flex items-center gap-3 bg-card border border-border px-4 py-2 rounded-full shadow-sm">
                            <div className={`w-3 h-3 rounded-full ${criticalCount > 0 ? 'bg-status-red animate-pulse' : 'bg-status-green'} `}></div>
                            <span className="font-medium text-sm text-foreground">
                                {criticalCount > 0 ? "System Attention Required" : "All Systems Nominal"}
                            </span>
                        </div>

                        <AddSensorModal onSensorCreated={handleSensorCreated} />
                    </div>
                </div>

                {/* KPI Overview */}
                {(criticalCount > 0 || warningCount > 0) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {criticalCount > 0 && (
                            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 flex items-center gap-4">
                                <ShieldAlert className="w-8 h-8 text-status-red" />
                                <div>
                                    <h4 className="font-semibold text-status-red">Calibration Required</h4>
                                    <p className="text-sm text-muted-foreground">{criticalCount} probes showing significant drift or failure.</p>
                                </div>
                            </div>
                        )}
                        {warningCount > 0 && (
                            <div className="bg-status-yellow/10 border border-status-yellow/20 rounded-lg p-4 flex items-center gap-4">
                                <Activity className="w-8 h-8 text-status-yellow" />
                                <div>
                                    <h4 className="font-semibold text-status-yellow">Maintenance Warning</h4>
                                    <p className="text-sm text-muted-foreground">{warningCount} probes nearing end of life or require cleaning.</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Sensor Grid */}
                <div>
                    <div className="flex justify-between items-end mb-4">
                        <h2 className="text-xl font-semibold text-foreground">Active Instrumentation</h2>
                        <span className="text-sm text-muted-foreground">Total: {sensors.length}</span>
                    </div>
                    {loading ? (
                        <div className="text-center py-20 text-muted-foreground">Loading sensors...</div>
                    ) : sensors.length === 0 ? (
                        <div className="text-center py-20 border border-dashed rounded-lg">
                            <p className="text-muted-foreground mb-4">No sensors found.</p>
                            <AddSensorModal onSensorCreated={handleSensorCreated} />
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {sensors.map((sensor) => (
                                <SmartSensorCard key={sensor.id} {...sensor} />
                            ))}
                        </div>
                    )}
                </div>

                {/* System Health Overview Chart */}
                <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
                    <div className="mb-6">
                        <h3 className="text-lg font-semibold text-foreground">Maintenance Priority: Lowest Health Sensors</h3>
                        <p className="text-sm text-muted-foreground">Sensors requiring immediate attention based on analysis scores.</p>
                    </div>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                data={[...sensors].sort((a, b) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 10)}
                                layout="vertical"
                                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#2D3748" />
                                <XAxis type="number" domain={[0, 100]} hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    width={100}
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                />
                                <Tooltip
                                    cursor={{ fill: '#2D3748', opacity: 0.4 }}
                                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: '#fff' }}
                                />
                                <Bar dataKey="healthScore" radius={[0, 4, 4, 0]} barSize={20}>
                                    {
                                        [...sensors].sort((a, b) => (a.healthScore || 0) - (b.healthScore || 0)).slice(0, 10).map((entry, index) => {
                                            const score = entry.healthScore || 0;
                                            let fill = '#00C851'; // Normal
                                            if (score < 50 || entry.status === 'Critical') fill = '#ff4444'; // Critical
                                            else if (score < 80 || entry.status === 'Warning') fill = '#ffbb33'; // Warning

                                            return <Cell key={`cell-${index}`} fill={fill} />;
                                        })
                                    }
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
