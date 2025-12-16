"use client";

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    ScatterChart, Scatter, ReferenceLine, Brush
} from 'recharts';
import {
    Activity, ArrowLeft, AlertTriangle, FileText,
    CheckCircle, Zap, TrendingUp, Droplets, RefreshCcw, Wrench
} from 'lucide-react';
import Link from 'next/link';
import { api } from "@/lib/api";
import { DataUploadModal } from "@/components/DataUploadModal";

interface SensorClientProps {
    sensorId: string;
}

export default function SensorClient({ sensorId }: SensorClientProps) {
    const [activeTab, setActiveTab] = useState<'diagnosis' | 'signal' | 'expert'>('diagnosis');
    const [isReportModalOpen, setIsReportModalOpen] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [dataset, setDataset] = useState<number[]>([]);
    const [hasData, setHasData] = useState(false);
    const [generatingReport, setGeneratingReport] = useState(false);

    const fetchData = async (start?: string, end?: string) => {
        if (!analysisResult) setLoading(true);
        else setIsRefreshing(true);

        try {
            const savedConfig = localStorage.getItem("qorsense_config");
            const config = savedConfig ? JSON.parse(savedConfig) : undefined;
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
        fetchData();
    };

    const handleDownloadReport = async () => {
        if (!analysisResult) return;
        setGeneratingReport(true);
        try {
            const blob = await api.generateReport(analysisResult, dataset);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Analysis_Report_${sensorId}_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            window.alert("Report Downloaded Successfully!");
            setIsReportModalOpen(false);
        } catch (error) {
            console.error("Report generation failed:", error);
            window.alert("Failed to generate report.");
        } finally {
            setGeneratingReport(false);
        }
    };

    const healthDetails = analysisResult ? {
        score: analysisResult.health_score,
        status: analysisResult.status,
        diagnosis: analysisResult.diagnosis
    } : { score: 0, status: 'Grey', diagnosis: 'No Data' };

    return (
        <div className="min-h-screen bg-background pb-20">
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 space-y-2">
                        <div className="flex items-center gap-3">
                            <Badge variant="outline" className="text-muted-foreground border-muted-foreground">ID: {sensorId}</Badge>
                        </div>
                        <h1 className="text-4xl font-bold text-foreground">Sensor Analysis</h1>
                        <div className="flex items-center gap-4 mt-2">
                            {!hasData && (
                                <DataUploadModal sensorId={sensorId} onUploadSuccess={handleUploadSuccess} />
                            )}
                            <Button variant="ghost" onClick={() => fetchData()} disabled={loading}>
                                <RefreshCcw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                                Refresh Analysis
                            </Button>
                        </div>
                    </div>
                    {hasData && (
                        <Card className={`text-center flex flex-col justify-center py-6 border-2 ${healthDetails.status === 'Critical' ? 'bg-status-red/10 border-status-red/20' : 'bg-status-yellow/10 border-status-yellow/20'}`}>
                            <div className="text-sm uppercase tracking-widest text-muted-foreground font-semibold mb-1">Estimated Drift Limit (RUL)</div>
                            <div className={`text-4xl font-black ${healthDetails.status === 'Critical' ? 'text-status-red' : 'text-status-yellow'} tracking-tighter`}>
                                {loading ? "..." : (analysisResult?.prediction || "Unknown")}
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

                        <div className="lg:col-span-3">
                            <div className="flex border-b border-border mb-6">
                                <button onClick={() => setActiveTab('diagnosis')} className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'diagnosis' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Diagnosis</button>
                                <button onClick={() => setActiveTab('signal')} className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'signal' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Raw Signal</button>
                                <button onClick={() => setActiveTab('expert')} className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'expert' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Expert Analysis</button>
                            </div>
                            <div className="bg-card border border-border rounded-xl p-6 min-h-[400px]">
                                {activeTab === 'diagnosis' && (
                                    <div className="space-y-6">
                                        <h3 className="text-lg font-semibold flex items-center gap-2">
                                            <TrendingUp className="w-5 h-5 text-status-yellow" />
                                            Signal Stability / Drift
                                        </h3>
                                        <div className="h-[300px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={analysisResult?.metrics?.hysteresis_x ? analysisResult.metrics.hysteresis_x.map((_: any, i: number) => ({ index: i, value: analysisResult.metrics.hysteresis_y[i] })) : []}>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                    <XAxis dataKey="index" stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                                                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }} />
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
                                        <div className="h-[300px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={analysisResult ? analysisResult.metrics.hysteresis_x.map((val: any, i: number) => ({ index: i, raw: val })) : []}>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2D3748" />
                                                    <XAxis dataKey="index" stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                    <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                                                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }} />
                                                    <Line type="monotone" dataKey="raw" stroke="#4A5568" strokeWidth={1} dot={false} name="Raw Input" isAnimationActive={false} />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                                {activeTab === 'expert' && (
                                    <div className="text-center text-muted-foreground py-20">
                                        Expert analysis data available in detailed view.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {isReportModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="bg-card w-full max-w-md rounded-xl border border-border shadow-2xl p-6">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-xl font-bold">Generate Report</h3>
                            <button onClick={() => setIsReportModalOpen(false)} className="text-muted-foreground hover:text-foreground">✕</button>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <Button className="w-full bg-primary hover:bg-primary-end" onClick={handleDownloadReport} disabled={generatingReport}>
                                {generatingReport ? "Generating PDF..." : "Download Official Report (PDF)"}
                            </Button>
                            <Button variant="outline" className="w-full" onClick={() => setIsReportModalOpen(false)}>Cancel</Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
