"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch" // Assuming standard Shadcn switch, if not I'll just use a checkbox or simulate it
import { Button } from "@/components/ui/button"
import { Settings, Save, RotateCcw } from "lucide-react"

// Default configuration
const DEFAULT_CONFIG = {
    slopeThreshold: 0.05,
    biasLimit: 0.1,
    noiseTolerance: 0.5,
    compactMode: false
};

export default function SettingsPage() {
    const [config, setConfig] = useState(DEFAULT_CONFIG);
    const [status, setStatus] = useState("");

    // Load settings from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem("qorsense_config");
        if (saved) {
            try {
                setConfig({ ...DEFAULT_CONFIG, ...JSON.parse(saved) });
            } catch (e) {
                console.error("Failed to parse settings", e);
            }
        }
    }, []);

    const handleSave = () => {
        localStorage.setItem("qorsense_config", JSON.stringify(config));
        setStatus("Settings saved successfully!");
        setTimeout(() => setStatus(""), 3000);
    };

    const handleReset = () => {
        setConfig(DEFAULT_CONFIG);
        localStorage.removeItem("qorsense_config");
        setStatus("Settings reset to defaults.");
        setTimeout(() => setStatus(""), 3000);
    };

    return (
        <div className="container mx-auto p-6 space-y-8 max-w-4xl">
            <div className="flex items-center gap-3 mb-6">
                <Settings className="h-8 w-8 text-primary" />
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Control Room</h1>
                    <p className="text-muted-foreground">Manage analysis algorithms and interface preferences.</p>
                </div>
            </div>

            <div className="grid gap-6">
                {/* Analysis Sensitivity Section */}
                <Card>
                    <CardHeader>
                        <CardTitle>Analysis Sensitivity</CardTitle>
                        <CardDescription>
                            Fine-tune the algorithms used for sensor health detection. Changes affect future analysis requests.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                        {/* Slope Threshold */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <Label className="text-base font-medium">Slope Threshold (Drift Detection)</Label>
                                <span className="text-sm text-primary font-mono bg-primary/10 px-2 py-1 rounded">
                                    {config.slopeThreshold.toFixed(3)}
                                </span>
                            </div>
                            <Slider
                                value={[config.slopeThreshold]}
                                min={0.001}
                                max={0.2}
                                step={0.001}
                                onValueChange={(vals) => setConfig({ ...config, slopeThreshold: vals[0] })}
                            />
                            <p className="text-xs text-muted-foreground">
                                Lower values make the system more sensitive to minor trends (potential false positives). Higher values ignore slow drifts.
                            </p>
                        </div>

                        {/* Bias Limit */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <Label className="text-base font-medium">Bias Limit (Offset)</Label>
                                <span className="text-sm text-primary font-mono bg-primary/10 px-2 py-1 rounded">
                                    {config.biasLimit.toFixed(2)}
                                </span>
                            </div>
                            <Slider
                                value={[config.biasLimit]}
                                min={0.01}
                                max={1.0}
                                step={0.01}
                                onValueChange={(vals) => setConfig({ ...config, biasLimit: vals[0] })}
                            />
                            <p className="text-xs text-muted-foreground">
                                Maximum allowable constant deviation from the baseline before triggering a warning.
                            </p>
                        </div>

                        {/* Noise Tolerance */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <Label className="text-base font-medium">Noise Tolerance (SNR)</Label>
                                <span className="text-sm text-primary font-mono bg-primary/10 px-2 py-1 rounded">
                                    {config.noiseTolerance.toFixed(2)}
                                </span>
                            </div>
                            <Slider
                                value={[config.noiseTolerance]}
                                min={0.1}
                                max={2.0}
                                step={0.1}
                                onValueChange={(vals) => setConfig({ ...config, noiseTolerance: vals[0] })}
                            />
                            <p className="text-xs text-muted-foreground">
                                Threshold for signal-to-noise ratio. Higher values allow noisier signals without flagging 'Critical'.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Appearance Section */}
                <Card>
                    <CardHeader>
                        <CardTitle>Interface Preferences</CardTitle>
                        <CardDescription>Customize the look and feel of the dashboard.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base">Compact Mode</Label>
                                <p className="text-xs text-muted-foreground">Reduce padding and font sizes for high-density displays.</p>
                            </div>
                            {/* Using a simple checkbox styled as switch if shadcn Switch isn't available, but standard shadcn usually has it. 
                                I'll assume Switch is not imported in my check earlier or missed, but I'll use a checkbox as fallback if needed or a simple toggle.
                                Actually I will use a simple checkbox implemented with standard HTML for updating locally since I don't want to break if Switch is missing. 
                                Wait, I saw components/ui folder but I didn't see switch.tsx in list list_dir results earlier (it had slider, select, etc).
                                So I will implement a custom simple toggle to be safe.
                            */}
                            <div
                                className={`w-12 h-6 rounded-full p-1 cursor-pointer transition-colors ${config.compactMode ? 'bg-primary' : 'bg-muted'}`}
                                onClick={() => setConfig({ ...config, compactMode: !config.compactMode })}
                            >
                                <div className={`w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${config.compactMode ? 'translate-x-6' : 'translate-x-0'}`} />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-4">
                    <Button variant="outline" onClick={handleReset} className="gap-2">
                        <RotateCcw className="w-4 h-4" /> Reset Defaults
                    </Button>
                    <Button onClick={handleSave} className="gap-2 min-w-[120px]">
                        <Save className="w-4 h-4" /> Save Changes
                    </Button>
                </div>

                {status && (
                    <div className="fixed bottom-6 right-6 bg-foreground text-background px-4 py-2 rounded shadow-lg animate-in fade-in slide-in-from-bottom-5">
                        {status}
                    </div>
                )}
            </div>
        </div>
    )
}
