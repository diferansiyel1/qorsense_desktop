"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer,
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip
} from 'recharts';
import {
    Activity, Download, RefreshCw, AlertTriangle, CheckCircle, Zap
} from 'lucide-react';
import { api, Sensor } from '@/lib/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// --- Types ---
interface AnalysisMetrics {
    bias: number;
    slope: number;
    noise_std: number;
    hysteresis: number;
    hurst: number;
    [key: string]: number;
}

interface NormalizedMetric {
    subject: string;
    A: number; // Normalized Score (0-100)
    fullMark: number;
    raw: number;
    unit: string;
    description: string;
}

// --- Constants & Thresholds ---
const THRESHOLDS = {
    bias: 2.0,
    slope: 0.1,
    noise_std: 1.5,
    hysteresis: 0.5,
    hurst: 0.8 // Inverted logic for Hurst often, but using simplified 0.8 threshold here
};

const METRIC_CONFIG = {
    bias: { label: "Bias", desc: "Kalibrasyon sapması", unit: "" },
    slope: { label: "Slope", desc: "Sensör yaşlanma hızı", unit: "" },
    noise_std: { label: "Noise", desc: "Sinyal kirliliği", unit: "dB" },
    hysteresis: { label: "Hysteresis", desc: "Tepki süresinde takılma", unit: "" },
    hurst: { label: "DFA", desc: "Kararlılık kaybı", unit: "" }
};

export default function SensorAnalysisCockpit() {
    // --- State ---
    const [sensors, setSensors] = useState<Sensor[]>([]);
    const [selectedSensorId, setSelectedSensorId] = useState<string>("");
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [generatingReport, setGeneratingReport] = useState(false);

    // --- Data Fetching ---
    useEffect(() => {
        const fetchSensors = async () => {
            try {
                const response = await api.getSensors();
                const sensorsData = (response as any).items ? (response as any).items : response;

                setSensors(sensorsData);
                if (sensorsData.length > 0) {
                    setSelectedSensorId(sensorsData[0].id);
                }
            } catch (err) {
                console.error("Failed to fetch sensors", err);
            }
        };
        fetchSensors();
    }, []);

    useEffect(() => {
        if (!selectedSensorId) return;

        const analyze = async () => {
            setLoading(true);
            try {
                // Get Settings
                const savedConfig = localStorage.getItem("qorsense_config");
                const config = savedConfig ? JSON.parse(savedConfig) : undefined;

                const result = await api.analyzeSensor(selectedSensorId, config);
                setAnalysisResult(result);
            } catch (err) {
                console.error("Analysis failed", err);
                setAnalysisResult(null);
            } finally {
                setLoading(false);
            }
        };
        analyze();
    }, [selectedSensorId]);

    // --- Normalization Logic ---
    const normalizedData = useMemo(() => {
        if (!analysisResult?.metrics) return [];

        const metrics = analysisResult.metrics as AnalysisMetrics;

        // Normalize function: (Value / Threshold) * 100, clamped at 100
        const norm = (val: number, threshold: number) => Math.min(100, (Math.abs(val) / threshold) * 100);

        return [
            {
                subject: 'Bias',
                A: norm(metrics.bias, THRESHOLDS.bias),
                fullMark: 100,
                raw: metrics.bias,
                unit: METRIC_CONFIG.bias.unit,
                description: METRIC_CONFIG.bias.desc
            },
            {
                subject: 'Slope',
                A: norm(metrics.slope, THRESHOLDS.slope),
                fullMark: 100,
                raw: metrics.slope,
                unit: METRIC_CONFIG.slope.unit,
                description: METRIC_CONFIG.slope.desc
            },
            {
                subject: 'Noise',
                A: norm(metrics.noise_std, THRESHOLDS.noise_std),
                fullMark: 100,
                raw: metrics.noise_std,
                unit: METRIC_CONFIG.noise_std.unit,
                description: METRIC_CONFIG.noise_std.desc
            },
            {
                subject: 'Hysteresis',
                A: norm(metrics.hysteresis, THRESHOLDS.hysteresis),
                fullMark: 100,
                raw: metrics.hysteresis,
                unit: METRIC_CONFIG.hysteresis.unit,
                description: METRIC_CONFIG.hysteresis.desc
            },
            {
                subject: 'DFA',
                A: norm(Math.abs(0.5 - metrics.hurst) * 2, 0.5), // Custom logic for DFA distance from 0.5
                fullMark: 100,
                raw: metrics.hurst,
                unit: METRIC_CONFIG.hurst.unit,
                description: METRIC_CONFIG.hurst.desc
            },
        ];
    }, [analysisResult]);

    // --- Report Generation ---
    const handleGenerateReport = async () => {
        if (!analysisResult) return;
        setGeneratingReport(true);
        try {
            // Using raw data from analysis result if available, otherwise empty
            const rawData = analysisResult.metrics.hysteresis_x || [];
            const blob = await api.generateReport(analysisResult, rawData);

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Cockpit_Report_${selectedSensorId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            alert("Report generated successfully!");
        } catch (error) {
            console.error("Report generation error", error);
            alert("Failed to generate report.");
        } finally {
            setGeneratingReport(false);
        }
    };

    // --- Helpers ---
    const getStatusColor = (val: number) => {
        if (val < 50) return "text-status-green";
        if (val < 80) return "text-status-yellow";
        return "text-status-red";
    };

    const getStatusText = (val: number) => {
        if (val < 50) return "Normal";
        if (val < 80) return "Warning";
        return "Critical";
    };

    const trendData = useMemo(() => {
        if (!analysisResult?.metrics?.hysteresis_x) return [];
        // Use hysteresis_x as a proxy for raw signal time series for now, as existing code did
        return analysisResult.metrics.hysteresis_x.map((val: number, i: number) => ({
            time: i,
            value: val
        })).slice(0, 50); // Show last 50 points
    }, [analysisResult]);


    return (
        <div className="min-h-screen bg-background pb-20 p-6 space-y-8 max-w-[1400px] mx-auto">

            {/* 1. Header Area */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border/50 pb-6">
                <div>
                    <h1 className="text-4xl font-black tracking-tight text-foreground flex items-center gap-3">
                        <Activity className="w-8 h-8 text-primary" />
                        Sensor Cockpit
                    </h1>
                    <p className="text-muted-foreground mt-1">Real-time health monitoring and anomaly detection.</p>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <Select value={selectedSensorId} onValueChange={setSelectedSensorId}>
                        <SelectTrigger className="w-[250px] bg-card border-border">
                            <SelectValue placeholder="Select Sensor" />
                        </SelectTrigger>
                        <SelectContent>
                            {sensors.map(s => (
                                <SelectItem key={s.id} value={s.id}>
                                    {s.name} <span className="text-xs text-muted-foreground ml-2">({s.location})</span>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <Button
                        onClick={handleGenerateReport}
                        disabled={generatingReport || loading || !analysisResult}
                        className="bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 transition-all shadow-lg shadow-primary/20"
                    >
                        {generatingReport ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                        Generate Report
                    </Button>
                </div>
            </div>

            {loading && !analysisResult ? (
                <div className="h-96 flex flex-col items-center justify-center text-muted-foreground animate-pulse">
                    <RefreshCw className="w-12 h-12 mb-4 animate-spin text-primary" />
                    <p>Initializing Sensor Analysis...</p>
                </div>
            ) : !analysisResult ? (
                <div className="h-64 flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                    <AlertTriangle className="w-10 h-10 mb-2" />
                    No analysis data available. Please select a sensor or upload data.
                </div>
            ) : (
                <>
                    {/* 2. Top Metric Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        {normalizedData.map((metric) => (
                            <Card key={metric.subject} className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-colors">
                                <CardContent className="p-5 flex flex-col items-start justify-between h-full">
                                    <div className="w-full flex justify-between items-start mb-2">
                                        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">{metric.subject}</h3>
                                        <Badge variant="outline" className={`${getStatusColor(metric.A)} border-current bg-transparent opacity-80`}>
                                            {getStatusText(metric.A)}
                                        </Badge>
                                    </div>
                                    <div className="mb-1">
                                        <div className={`text-3xl font-bold ${getStatusColor(metric.A)}`}>
                                            {metric.raw.toFixed(4)} <span className="text-sm font-normal text-muted-foreground">{metric.unit}</span>
                                        </div>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-2 border-t border-border/30 pt-2 w-full">
                                        {metric.description}
                                    </p>
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    {/* 3. Middle Grid: Radar & Trend */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                        {/* Radar Chart */}
                        <Card className="lg:col-span-1 bg-card/40 border-border/50">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Zap className="w-5 h-5 text-status-yellow" />
                                    Multivariate Signature
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="h-[400px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={normalizedData}>
                                        <PolarGrid stroke="#2D3748" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />

                                        {/* Critical Zone Background */}
                                        <Radar
                                            name="Critical Zone"
                                            dataKey="fullMark"
                                            stroke="none"
                                            fill="#EF4444"
                                            fillOpacity={0.1}
                                        />
                                        {/* Safe Zone */}
                                        <Radar
                                            name="Safe Zone"
                                            dataKey="fullMark"
                                            stroke="none"
                                            fill="#10B981"
                                            fillOpacity={0.1}
                                        // Trying to limit radius visually is hard with just data, but this overlays
                                        />

                                        {/* Actual Data */}
                                        <Radar
                                            name="Current Status"
                                            dataKey="A"
                                            stroke="#00ADB5"
                                            strokeWidth={3}
                                            fill="#00ADB5"
                                            fillOpacity={0.4}
                                        />
                                        <RechartsTooltip
                                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }}
                                            itemStyle={{ color: '#fff' }}
                                        />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>

                        {/* Trend Chart */}
                        <Card className="lg:col-span-2 bg-card/40 border-border/50">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Activity className="w-5 h-5 text-primary" />
                                    Live Signal Trend
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="h-[400px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={trendData}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                        <XAxis dataKey="time" stroke="#94a3b8" tickLine={false} axisLine={false} />
                                        <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                                        <RechartsTooltip
                                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="value"
                                            stroke="#F59E0B"
                                            strokeWidth={2}
                                            dot={false}
                                            activeDot={{ r: 6, fill: '#F59E0B' }}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>
                    </div>

                    {/* 4. AI Insight Summary (Bonus) */}
                    <Card className="bg-primary/5 border-primary/20">
                        <CardContent className="p-6 flex items-start gap-4">
                            <CheckCircle className="w-6 h-6 text-primary mt-1" />
                            <div>
                                <h3 className="font-bold text-lg text-primary">AI Diagnostic Assessment</h3>
                                <p className="text-foreground/80 mt-1 leading-relaxed">
                                    {analysisResult.diagnosis || "System is operating within expected parameters."}
                                    {analysisResult.recommendation && ` Recommendation: ${analysisResult.recommendation}`}
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
