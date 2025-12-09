"use client";

import { useState, useCallback } from "react";
import { SimulationControls, SimulationConfig } from "@/components/simulation/SimulationControls";
import { InteractiveAnalysisChart } from "@/components/simulation/InteractiveAnalysisChart";
import { AnalysisResultsPanel } from "@/components/simulation/AnalysisResultsPanel";

export default function SimulationPage() {
    const [data, setData] = useState<any[]>([]);
    const [currentConfig, setCurrentConfig] = useState<SimulationConfig | null>(null);
    const [result, setResult] = useState<any>(null);
    const [previousResult, setPreviousResult] = useState<any>(null);
    const [brushRange, setBrushRange] = useState<{ start: number, end: number } | null>(null);

    // Helpers to generate synthetic data
    const generateData = (config: SimulationConfig) => {
        const points = [];
        for (let i = 0; i < config.duration; i++) {
            let value = 0;
            // Signal Type Logic
            if (config.signalType === 'drift') {
                value = i * 0.1; // Linear drift
            } else if (config.signalType === 'oscillation') {
                value = Math.sin(i * 0.2) * 10;
            } else if (config.signalType === 'biofilm') {
                value = Math.exp(i * 0.05);
            }

            // Add Noise
            const noise = (Math.random() - 0.5) * config.noiseLevel;
            value += noise;

            points.push({ index: i, value });
        }
        return points;
    };

    // Mock Analysis Logic (Client-side for speed, would be API in real app)
    const analyzeData = (dataSegment: any[], config: SimulationConfig) => {
        const values = dataSegment.map(d => d.value);
        const mean = values.reduce((a, b) => a + b, 0) / values.length;

        // Simple Linear Regression for Slope
        const n = values.length;
        const indices = Array.from({ length: n }, (_, i) => i);
        const sumX = indices.reduce((a, b) => a + b, 0);
        const sumY = values.reduce((a, b) => a + b, 0);
        const sumXY = indices.map((x, i) => x * values[i]).reduce((a, b) => a + b, 0);
        const sumXX = indices.map(x => x * x).reduce((a, b) => a + b, 0);
        const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);

        // Simple Random Walk DFA approx (Hurst)
        // Truly calculating DFA is complex client-side, using a proxy
        const range = Math.max(...values) - Math.min(...values);
        const stdDev = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b) / n);
        const dfa = (range / stdDev) * 0.1; // Toy calculation

        // Determine Health Score based on user thresholds (Tuning)
        let violations = 0;
        if (Math.abs(mean) > config.criticalBias) violations++;
        if (Math.abs(slope) > config.criticalSlope) violations++;
        if (dfa > config.dfaThreshold) violations++;

        let score = 100 - (violations * 30);
        if (score < 0) score = 0;

        let diagnosis = "Optimal Operation";
        if (score < 40) diagnosis = "Critical Failure Imminent";
        else if (score < 70) diagnosis = "Maintenance Recommended";

        return {
            healthScore: score,
            bias: mean,
            slope: slope,
            dfa: dfa,
            hysteresisArea: Math.random() * 10, // Mock
            diagnosis
        };
    };

    const handleRun = (config: SimulationConfig) => {
        const newData = generateData(config);
        setData(newData);
        setCurrentConfig(config);

        // Save current result as previous before updating
        if (result) setPreviousResult(result);

        const res = analyzeData(newData, config);
        setResult(res);
        setBrushRange(null); // Reset brush
    };

    const handleUpload = (uploadedData: any[]) => {
        setData(uploadedData);
        setResult(null);
        setPreviousResult(null);
        setBrushRange(null);
        // Default config for upload mode if needed, or keep existing
        if (currentConfig) {
            setCurrentConfig({ ...currentConfig, sourceType: 'upload' });
        }
    };

    const handleReset = () => {
        setData([]);
        setResult(null);
        setPreviousResult(null);
        setBrushRange(null);
    };

    const handleBrushChange = useCallback((start: number, end: number) => {
        setBrushRange({ start, end });
        if (data.length > 0 && currentConfig) {
            const slicedData = data.slice(start, end + 1);
            const res = analyzeData(slicedData, currentConfig);
            setResult(res);
            // Note: In diff view, we might want to compare sliced vs full? 
            // Or typically: compare previous analysis vs current. 
            // Here, just updating current result to reflect slice.
        }
    }, [data, currentConfig]);

    return (
        <div className="h-[calc(100vh-4rem)] bg-background p-4 grid grid-cols-12 gap-4">
            {/* Left Panel: Controls (3 Cols) */}
            <div className="col-span-3 h-full">
                <SimulationControls
                    onRun={handleRun}
                    onReset={handleReset}
                    onUpload={handleUpload}
                />
            </div>

            {/* Right Panel: Chart & Results (9 Cols) */}
            <div className="col-span-9 h-full flex flex-col gap-4">
                {/* Top: Chart (70%) */}
                <div className="flex-[3] h-0">
                    <InteractiveAnalysisChart
                        data={data}
                        config={currentConfig || {} as any}
                        onBrushChange={handleBrushChange}
                    />
                </div>

                {/* Bottom: Results (30%) */}
                <div className="flex-1 h-0">
                    <AnalysisResultsPanel result={result} previousResult={previousResult} />
                </div>
            </div>
        </div>
    );
}
