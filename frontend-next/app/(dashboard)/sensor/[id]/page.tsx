"use client";

import { useState, use, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    ScatterChart, Scatter, ReferenceLine, Brush
} from 'recharts';
import {
    Activity, ArrowLeft, AlertTriangle, Calendar, FileText,
    CheckCircle, Zap, Settings, TrendingUp, Droplets, RefreshCcw, Wrench
} from 'lucide-react';
import Link from 'next/link';
import { api } from "@/lib/api";
import { DataUploadModal } from "@/components/DataUploadModal";

// Mock Data removed in favor of API fetching

export default function SensorDetailPage(props: { params: Promise<{ id: string }> }) {
    // Unwrap params using React.use()
    const params = use(props.params);
    const sensorId = params.id;
    const [activeTab, setActiveTab] = useState<'diagnosis' | 'signal' | 'expert'>('diagnosis');
    const [isReportModalOpen, setIsReportModalOpen] = useState(false);

    // State for Real Data
    const [analysisResult, setAnalysisResult] = useState<any>(null); // Using any for speed, ideally typed
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [dataset, setDataset] = useState<number[]>([]); // Store raw data for report
    const [hasData, setHasData] = useState(false);
    const [generatingReport, setGeneratingReport] = useState(false);

    // Initial Fetch
    // We will simulate fetching specific sensor data type based on ID
    // ID 1: Normal, ID 2: Drifting, ID 3: Noisy
    const fetchData = async (start?: string, end?: string) => {
        // Only set main loading on initial load or if we really want to clear everything
        // For range updates, use isRefreshing to keep chart mounted
        if (!analysisResult) setLoading(true);
        else setIsRefreshing(true);

        try {
            // Retrieve settings from localStorage
            const savedConfig = localStorage.getItem("qorsense_config");
            const config = savedConfig ? JSON.parse(savedConfig) : undefined;

            // Try to analyze existing data with optional config
            const requestConfig = config || {};
            if (start && end) {
                requestConfig.start_date = start;
                requestConfig.end_date = end;
            }

            const result = await api.analyzeSensor(sensorId, requestConfig);

            if (result && result.status === "No Data") {
                setHasData(false);
                setAnalysisResult(null);
            } else if (result && result.metrics && result.metrics.hysteresis_x) {
                setDataset(result.metrics.hysteresis_x);
                setHasData(true);
                setAnalysisResult(result);
            } else {
                setDataset([]);
                setHasData(true);
                setAnalysisResult(result);
            }
        } catch (error: any) {
            if (error?.response?.status !== 404) {
                console.error("Failed to fetch data:", error);
            }
            // If 404/500, likely no data
            setHasData(false);
            setAnalysisResult(null);
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    };


    useEffect(() => {
        fetchData();
    }, [sensorId]);

    const handleUploadSuccess = () => {
        // Data uploaded, now we can analyze
        fetchData();
    };

    const handleDownloadReport = async () => {
        if (!analysisResult) return;
        setGeneratingReport(true);
        try {
            // Generate report blob
            const blob = await api.generateReport(analysisResult, dataset);

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Analysis_Report_${sensorId}_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Notify user (using alert for now as toast isn't fully set up in this context)
            // toast({ title: "Report Ready", description: "PDF has been downloaded." }) 
            // Using a temporary UI feedback instead of blocking alert if possible, but alert is consistent with existing modal style
            window.alert("Report Downloaded Successfully!");
            setIsReportModalOpen(false);

        } catch (error) {
            console.error("Report generation failed:", error);
            window.alert("Failed to generate report.");
        } finally {
            setGeneratingReport(false);
        }
    };

    // Mock Sensor Info based on ID
    const isCritical = analysisResult ? analysisResult.status === 'Critical' : false; // Adjusted from Red to Critical based on prompt/api logic
    const healthDetails = analysisResult ? {
        score: analysisResult.health_score,
        status: analysisResult.status,
        diagnosis: analysisResult.diagnosis
    } : { score: 0, status: 'Grey', diagnosis: 'No Data' };

    // Logic to simulate different types based on ID
    const getSensorType = (id: string) => {
        if (id === '1') return { name: 'Bioreactor pH Probe 01', type: 'pH Sensor' };
        if (id === '2') return { name: 'DO Probe @ Mix Tank', type: 'Dissolved Oxygen' };
        if (id === '3') return { name: 'Main Line Flowmeter', type: 'Electromagnetic Flow' };
        return { name: `Pressure TX-${id}01`, type: 'Pressure Transmitter' };
    };

    const sensorInfo = getSensorType(sensorId);



    return (
        <div className="min-h-screen bg-background pb-20">
            {/* Top Navigation */}
            <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/" className="flex items-center text-muted-foreground hover:text-foreground transition-colors">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Back to Dashboard
                    </Link>
                    <div className="flex items-center gap-4">
                        <Button
                            variant="outline"
                            className="text-status-green border-status-green/50 hover:bg-status-green/10"
                            onClick={() => setIsReportModalOpen(true)}
                            disabled={!hasData}
                        >
                            <FileText className="w-4 h-4 mr-2" />
                            Generate Calibration Report
                        </Button>
                        <Button
                            className="bg-primary hover:bg-primary-end text-white"
                            onClick={() => window.location.href = `/maintenance?sensorId=${sensorId}&action=new`}
                            disabled={!hasData}
                        >
                            <Wrench className="w-4 h-4 mr-2" />
                            Schedule Maintenance
                        </Button>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">

                {/* Header Section: The "Doctor's Chart" */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 space-y-2">
                        <div className="flex items-center gap-3">
                            <Badge variant="outline" className="text-muted-foreground border-muted-foreground">ID: {sensorId}</Badge>
                            {/* We could fetch sensor details separately if we wanted name/type here, for now using ID */}
                        </div>
                        <h1 className="text-4xl font-bold text-foreground">Sensor Analysis</h1>
                        <div className="flex items-center gap-4 mt-2">
                            {!hasData && (
                                <DataUploadModal sensorId={sensorId} onUploadSuccess={handleUploadSuccess} />
                            )}
                            <Button variant="ghost" onClick={fetchData} disabled={loading}>
                                <RefreshCcw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                                Refresh Analysis
                            </Button>
                        </div>
                    </div>

                    {/* RUL Counter */}
                    {hasData && (
                        <Card className={`text-center flex flex-col justify-center py-6 border-2 ${healthDetails.status === 'Critical' ? 'bg-status-red/10 border-status-red/20' : 'bg-status-yellow/10 border-status-yellow/20'}`}>
                            <div className="text-sm uppercase tracking-widest text-muted-foreground font-semibold mb-1">Estimated Drift Limit (RUL)</div>
                            <div className={`text-4xl font-black ${healthDetails.status === 'Critical' ? 'text-status-red' : 'text-status-yellow'} tracking-tighter`}>
                                {loading ? "..." : (analysisResult?.prediction || "Unknown")}
                            </div>
                            <div className="mt-2 text-sm text-foreground/80 font-medium">
                                {healthDetails.status === 'Critical' ? "⚠️ Calibration/Replacement Required" : (analysisResult?.prediction?.includes('day') ? "Signal Drift Predicted" : "Stable Operation")}
                            </div>
                        </Card>
                    )}
                </div>

                {!hasData ? (
                    <div className="flex flex-col items-center justify-center py-20 border border-dashed rounded-xl bg-card/50">
                        <AlertTriangle className="w-16 h-16 text-muted-foreground mb-4" />
                        <h2 className="text-xl font-semibold mb-2">Waiting for Data...</h2>
                        <p className="text-muted-foreground mb-6">Please upload a CSV file to begin analysis.</p>
                        <DataUploadModal sensorId={sensorId} onUploadSuccess={handleUploadSuccess} />
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                        {/* Sidebar / Vitals */}
                        <div className="space-y-4">
                            <Card>
                                <CardHeader className="uppercase text-xs font-bold text-muted-foreground tracking-wider pb-2">Sensor Health</CardHeader>
                                <CardContent className="space-y-6">
                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-muted-foreground">Overall Score</span>
                                            <span className={`font-bold ${healthDetails.status === 'Critical' ? 'text-status-red' : healthDetails.status === 'Warning' ? 'text-status-yellow' : 'text-status-green'}`}>
                                                {loading ? '-' : healthDetails.score.toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="h-2 w-full rounded-full overflow-hidden">
                                            <div className={`h-full ${healthDetails.status === 'Critical' ? 'bg-status-red' : healthDetails.status === 'Warning' ? 'bg-status-yellow' : 'bg-status-green'}`} style={{ width: `${healthDetails.score}%` }}></div>
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-muted-foreground">Signal Noise (SNR)</span>
                                            <span className="font-bold text-foreground">{loading ? '-' : analysisResult?.metrics.snr_db.toFixed(1)} dB</span>
                                        </div>
                                        <div className="h-2 w-full rounded-full overflow-hidden">
                                            <div className="h-full bg-status-yellow" style={{ width: `${Math.min(100, (analysisResult?.metrics.snr_db || 0) * 2)}%` }}></div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card className="bg-primary/5 border-primary/20">
                                <CardContent className="p-4 flex items-start gap-3">
                                    <Zap className="w-5 h-5 text-primary mt-1" />
                                    <div>
                                        <h4 className="font-bold text-primary text-sm">AI Diagnosis</h4>
                                        <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                                            {loading ? "Analyzing sensor signature..." : (healthDetails.diagnosis || "System optimal.")}
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Tabbed Analysis Area */}
                        <div className="lg:col-span-3">
                            {/* Custom Tabs */}
                            <div className="flex border-b border-border mb-6">
                                <button
                                    onClick={() => setActiveTab('diagnosis')}
                                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'diagnosis' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                                >
                                    Diagnosis
                                </button>
                                <button
                                    onClick={() => setActiveTab('signal')}
                                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'signal' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                                >
                                    Raw Signal
                                </button>
                                <button
                                    onClick={() => setActiveTab('expert')}
                                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'expert' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                                >
                                    Expert Analysis
                                </button>
                            </div>

                            {/* Tab Content */}
                            <div className="bg-card border border-border rounded-xl p-6 min-h-[400px]">

                                {activeTab === 'diagnosis' && (
                                    <div className="space-y-6">
                                        <div className="flex justify-between items-center">
                                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                                <TrendingUp className="w-5 h-5 text-status-yellow" />
                                                Signal Stability / Drift
                                            </h3>
                                            <Badge variant="outline" className={`border-${healthDetails.status === 'Critical' ? 'status-red' : 'status-yellow'} text-${healthDetails.status === 'Critical' ? 'status-red' : 'status-yellow'} bg-${healthDetails.status === 'Critical' ? 'status-red' : 'status-yellow'}/5`}>
                                                {healthDetails.diagnosis || "Analyzing..."}
                                            </Badge>
                                        </div>
                                        <div className="h-[300px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={analysisResult?.metrics.hysteresis_x ? analysisResult.metrics.hysteresis_x.map((_: any, i: number) => ({ index: i, value: analysisResult.metrics.hysteresis_y[i] })) : []}>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                    <XAxis dataKey="index" stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                                                    <Tooltip
                                                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                                    />
                                                    <ReferenceLine y={0.8} stroke="#E53E3E" strokeDasharray="3 3" label={{ value: 'Max Tolerance', fill: '#00ADB', fontSize: 12 }} />
                                                    <Line type="monotone" dataKey="value" stroke="#af5ce0" strokeWidth={3} dot={{ r: 4, fill: '#0f172a', strokeWidth: 2 }} isAnimationActive={false} />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>
                                        <div className="p-4 bg-muted/50 rounded-lg border border-border text-sm">
                                            <p>Diagnosis: <strong>{analysisResult?.diagnosis}</strong>. Recommendation: <strong>{analysisResult?.recommendation}</strong></p>
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'signal' && (
                                    <div className="space-y-6">
                                        <h3 className="text-lg font-semibold flex items-center gap-2">
                                            <Droplets className="w-5 h-5 text-primary" />
                                            Raw Millivolt (mV) Input
                                        </h3>
                                        <div className="h-[300px] w-full relative">
                                            {isRefreshing && (
                                                <div className="absolute inset-0 bg-black/20 z-10 flex items-center justify-center rounded-lg backdrop-blur-[1px]">
                                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                                                </div>
                                            )}
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={analysisResult ? analysisResult.metrics.hysteresis_x.map((val: any, i: number) => ({
                                                    index: i,
                                                    time: analysisResult.metrics.timestamps ? new Date(analysisResult.metrics.timestamps[i]).getTime() : i,
                                                    raw: val,
                                                    dateStr: analysisResult.metrics.timestamps ? analysisResult.metrics.timestamps[i] : i
                                                })) : []}>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                    <XAxis
                                                        dataKey="index"
                                                        stroke="#94a3b8"
                                                        tickLine={false}
                                                        axisLine={false}
                                                        tickFormatter={(idx) => {
                                                            const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                            if (!ts) return idx;
                                                            const d = new Date(ts);
                                                            return d.getSeconds() === 0 ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(/^.*:(\d{2})$/, ':$1');
                                                        }}
                                                        type="number"
                                                        domain={['auto', 'auto']}
                                                        minTickGap={30}
                                                    />
                                                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                    <Tooltip
                                                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                                        labelFormatter={(idx) => {
                                                            const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                            return ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionDigits: 3 }) : idx;
                                                        }}
                                                    />
                                                    <Line type="monotone" dataKey="raw" stroke="#4A5568" strokeWidth={1} dot={false} name="Raw Input" isAnimationActive={false} />
                                                    <Brush
                                                        dataKey="index"
                                                        height={30}
                                                        stroke="#00ADB5"
                                                        tickFormatter={(idx) => {
                                                            const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                            return ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : idx;
                                                        }}
                                                        onChange={(range: any) => {
                                                            // We want to fetch data when user STOPS dragging (onDragEnd is better but Brush onChange fires constantly)
                                                            // For now, let's use a button or debounce?
                                                            // Recharts Brush doesn't have onDragEnd easily exposed in types sometimes.
                                                            // Let's rely on user clicking "Analyze Selection" or similar?
                                                            // Or just update local state and have a button?
                                                            // Requirement: "Kullanıcı sürüklemeyi bıraktığında (onDragEnd veya debounce ile)"
                                                            // Use debounce logic here if possible, or simpler: Update a 'selectedRange' state.
                                                        }}
                                                        onDragEnd={(range: any) => {
                                                            if (range && range.startIndex !== undefined && range.endIndex !== undefined) {
                                                                const timestamps = analysisResult?.metrics.timestamps;
                                                                if (timestamps) {
                                                                    const start = timestamps[range.startIndex];
                                                                    const end = timestamps[range.endIndex];
                                                                    // Trigger fetch
                                                                    fetchData(start, end);
                                                                }
                                                            }
                                                        }}
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
                                            <p className="text-xs text-center text-muted-foreground mt-2">
                                                💡 Drag the slider below to analyze a specific time range.
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'expert' && (
                                    <div className="space-y-6">
                                        <div className="space-y-6 mb-8">
                                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                                <Activity className="w-5 h-5 text-primary" />
                                                Detrended Signal Analysis (Trend vs Noise)
                                            </h3>
                                            <div className="h-[300px] w-full border border-border rounded-lg bg-card p-2">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={analysisResult?.metrics?.trend ? analysisResult.metrics.trend.map((val: any, i: number) => ({
                                                        index: i,
                                                        time: analysisResult.metrics.timestamps ? new Date(analysisResult.metrics.timestamps[i]).getTime() : i,
                                                        trend: val,
                                                        original: analysisResult.metrics.hysteresis_x[i]
                                                    })) : []}>
                                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                        <XAxis
                                                            dataKey="index"
                                                            stroke="#94a3b8"
                                                            tickLine={false}
                                                            axisLine={false}
                                                            tickFormatter={(idx) => {
                                                                const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                                if (!ts) return idx;
                                                                const d = new Date(ts);
                                                                return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                                                            }}
                                                            type="number"
                                                            domain={['auto', 'auto']}
                                                        />
                                                        <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                        <Tooltip
                                                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                                            labelFormatter={(idx) => {
                                                                const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                                return ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionDigits: 3 }) : idx;
                                                            }}
                                                        />
                                                        <Line type="monotone" dataKey="original" stroke="#4A5568" strokeWidth={1} dot={false} name="Original Signal" isAnimationActive={false} strokeOpacity={0.4} />
                                                        <Line type="monotone" dataKey="trend" stroke="#F59E0B" strokeWidth={2} dot={false} name="Extracted Trend" isAnimationActive={false} />
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                            <div className="h-[200px] w-full border border-border rounded-lg bg-card p-2">
                                                <h4 className="text-sm font-medium mb-2 text-muted-foreground">Residuals (Noise Component)</h4>
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={analysisResult?.metrics?.residuals ? analysisResult.metrics.residuals.map((val: any, i: number) => ({
                                                        index: i,
                                                        time: analysisResult.metrics.timestamps ? new Date(analysisResult.metrics.timestamps[i]).getTime() : i,
                                                        residual: val
                                                    })) : []}>
                                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                        <XAxis
                                                            dataKey="index"
                                                            stroke="#94a3b8"
                                                            tickLine={false}
                                                            axisLine={false}
                                                            hide
                                                        />
                                                        <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                        <Tooltip
                                                            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                                                            labelFormatter={(idx) => {
                                                                const ts = analysisResult?.metrics?.timestamps?.[idx];
                                                                return ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionDigits: 3 }) : idx;
                                                            }}
                                                        />
                                                        <Line type="monotone" dataKey="residual" stroke="#ef4444" strokeWidth={1} dot={false} name="Residuals" isAnimationActive={false} />
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            <div>
                                                <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                                                    <Activity className="w-5 h-5 text-primary" />
                                                    Hysteresis Loop (Phase Plot)
                                                </h3>
                                                <div className="h-[300px] w-full border border-border rounded-lg bg-card p-2">
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ScatterChart>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
                                                            <XAxis type="number" dataKey="x" name="Input" stroke="#94a3b8" label={{ value: 'Signal (t)', position: 'insideBottom', offset: -5 }} />
                                                            <YAxis type="number" dataKey="y" name="Output" stroke="#94a3b8" label={{ value: 'Signal (t+1)', angle: -90, position: 'insideLeft' }} />
                                                            <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }} />
                                                            <Scatter name="Hysteresis" data={analysisResult?.metrics.hysteresis_x.map((val: any, i: number) => ({ x: val, y: analysisResult.metrics.hysteresis_y[i] }))} fill="#af5ce0" line shape="circle" isAnimationActive={false} />
                                                        </ScatterChart>
                                                    </ResponsiveContainer>
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-2 text-center">Area: {analysisResult?.metrics.hysteresis.toFixed(4)} (Low = Elastic, High = Viscous/Lag)</p>
                                            </div>

                                            <div>
                                                <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                                                    <TrendingUp className="w-5 h-5 text-primary" />
                                                    DFA Analysis (Fractal)
                                                </h3>
                                                <div className="h-[300px] w-full border border-border rounded-lg bg-card p-2">
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ScatterChart>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#2D3748" />
                                                            <XAxis type="number" dataKey="x" name="Log Scale" stroke="#94a3b8" label={{ value: 'Log Scale', position: 'insideBottom', offset: -5 }} />
                                                            <YAxis type="number" dataKey="y" name="Log Fluctuation" stroke="#94a3b8" label={{ value: 'Log F(n)', angle: -90, position: 'insideLeft' }} />
                                                            <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }} />
                                                            <Scatter name="DFA Points" data={analysisResult?.metrics.dfa_scales.map((s: any, i: number) => ({ x: Math.log(s), y: Math.log(analysisResult.metrics.dfa_fluctuations[i]) }))} fill="#F59E0B" shape="cross" isAnimationActive={false} />
                                                        </ScatterChart>
                                                    </ResponsiveContainer>
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-2 text-center">Hurst Exponent: {analysisResult?.metrics.hurst.toFixed(2)} (0.5 = Random, &gt;0.5 = Persistent)</p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                            </div>
                        </div>
                    </div>
                )}


                {/* Modal / Report Confirmation */}
                {isReportModalOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                        <div className="bg-card w-full max-w-md rounded-xl border border-border shadow-2xl p-6 animate-in fade-in zoom-in-95 duration-200">
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-xl font-bold">Maintenance Validation</h3>
                                <button onClick={() => setIsReportModalOpen(false)} className="text-muted-foreground hover:text-foreground">✕</button>
                            </div>

                            <div className="space-y-4">
                                <div className="p-4 bg-status-green/10 border border-status-green/20 rounded-lg">
                                    <h4 className="font-semibold text-status-green flex items-center gap-2">
                                        <CheckCircle className="w-4 h-4" /> Impact Analysis
                                    </h4>
                                    <p className="text-sm mt-1 text-foreground">
                                        Replacing This Probe maintains process sterility compliance and prevents batch rejection (Est. Saved: $12,500).
                                    </p>
                                </div>

                                <p className="text-sm text-muted-foreground">
                                    A calibration certificate request has been generated. Proceed with scheduling?
                                </p>

                                <div className="flex gap-3 mt-6">
                                    <Button
                                        className="w-full bg-primary hover:bg-primary-end"
                                        onClick={handleDownloadReport}
                                        disabled={generatingReport}
                                    >
                                        {generatingReport ? (
                                            <>
                                                <RefreshCcw className="w-4 h-4 mr-2 animate-spin" />
                                                Generating PDF...
                                            </>
                                        ) : (
                                            "Download Official Report (PDF)"
                                        )}
                                    </Button>
                                    <Button variant="outline" className="w-full" onClick={() => setIsReportModalOpen(false)} disabled={generatingReport}>Cancel</Button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
