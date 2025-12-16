"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea, BarChart, Bar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisMetrics } from '@/types';

interface ChartsProps {
    data: number[];
    windowSize: number;
    metrics?: AnalysisMetrics;
}

export function Charts({ data, windowSize, metrics }: ChartsProps) {
    // Transform data for Recharts
    const chartData = data.map((val, idx) => ({ index: idx, value: val }));

    // Calculate histogram data
    const bins = 20;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const step = (max - min) / bins;
    const histData = Array.from({ length: bins }, (_, i) => {
        const start = min + i * step;
        const end = start + step;
        const count = data.filter(v => v >= start && v < end).length;
        return { bin: start.toFixed(2), count };
    });

    // Reference window (first 10%)
    const refEnd = Math.max(1, Math.floor(data.length * 0.1));

    // Radar Data Preparation
    const radarData = metrics ? [
        { subject: 'Bias', A: Math.min(100, Math.abs(metrics.bias) * 20), fullMark: 100 },
        { subject: 'Slope', A: Math.min(100, Math.abs(metrics.slope) * 1000), fullMark: 100 },
        { subject: 'Noise', A: Math.min(100, (metrics.noise_std ?? 0) * 50), fullMark: 100 },
        { subject: 'Hysteresis', A: Math.min(100, metrics.hysteresis * 100), fullMark: 100 },
        { subject: 'Hurst', A: (metrics.hurst ?? 0.5) * 100, fullMark: 100 },
        { subject: 'SNR', A: Math.min(100, metrics.snr_db), fullMark: 100 },
    ] : [];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="col-span-1 lg:col-span-2 bg-slate-gray border-slate-gray/50">
                <CardHeader>
                    <div className="flex justify-between items-center">
                        <CardTitle className="text-white">Sensor Output Over Time</CardTitle>
                        <div className="flex items-center gap-4">
                            <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-primary-start to-primary-end rounded-lg">
                                <div className="w-3 h-3 rounded-full bg-primary-accent ring-2 ring-offset-2 ring-offset-slate-gray ring-white"></div>
                                Raw Data
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#92adc9] bg-transparent rounded-lg hover:bg-lighter-gray">
                                <div className="w-3 h-3 rounded-full bg-accent-orange"></div>
                                Trend Line
                            </button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" strokeOpacity={0.2} />
                            <XAxis dataKey="index" stroke="#92adc9" />
                            <YAxis stroke="#92adc9" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1a202c', borderColor: '#2D3748', color: '#fff' }}
                                itemStyle={{ color: '#fff' }}
                            />
                            <ReferenceArea x1={0} x2={refEnd} strokeOpacity={0.3} fill="#7C3AED" fillOpacity={0.1} />
                            <Line type="monotone" dataKey="value" stroke="#3182CE" strokeWidth={2} dot={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <Card className="col-span-1 bg-slate-gray border-slate-gray/50">
                <CardHeader>
                    <CardTitle className="text-white">Multi-Metric Radar</CardTitle>
                </CardHeader>
                <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                            <PolarGrid stroke="#4A5568" strokeOpacity={0.3} />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#92adc9', fontSize: 12 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar
                                name="Metrics"
                                dataKey="A"
                                stroke="#7C3AED"
                                fill="#7C3AED"
                                fillOpacity={0.4}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1a202c', borderColor: '#2D3748', color: '#fff' }}
                            />
                        </RadarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <Card className="col-span-1 lg:col-span-3 bg-slate-gray border-slate-gray/50">
                <CardHeader>
                    <CardTitle className="text-white">Noise Distribution</CardTitle>
                </CardHeader>
                <CardContent className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={histData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" strokeOpacity={0.2} />
                            <XAxis dataKey="bin" stroke="#92adc9" fontSize={10} />
                            <YAxis stroke="#92adc9" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1a202c', borderColor: '#2D3748', color: '#fff' }}
                                itemStyle={{ color: '#fff' }}
                            />
                            <Bar dataKey="count" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
}
