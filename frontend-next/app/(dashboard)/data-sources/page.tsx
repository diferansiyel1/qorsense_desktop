"use client";

import { useEffect, useState, useCallback } from "react";
import { api, Sensor } from "@/lib/api";
import { DataUploadModal } from "@/components/DataUploadModal";
import { DeleteSensorModal } from "@/components/DeleteSensorModal";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Database } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DataSourcesPage() {
    const [sensors, setSensors] = useState<Sensor[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchSensors = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.getSensors();
            setSensors(data);
        } catch (error) {
            console.error("Failed to fetch sensors:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSensors();
    }, [fetchSensors]);

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
                    <p className="text-muted-foreground mt-1">
                        Manage your sensor connections and upload historical data.
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchSensors} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                </Button>
            </div>

            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        <CardTitle>Connected Sensors</CardTitle>
                    </div>
                    <CardDescription>
                        List of all configured sensors and their data ingestion status.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading && sensors.length === 0 ? (
                        <div className="flex justify-center items-center h-32 text-muted-foreground">
                            Loading sensors...
                        </div>
                    ) : sensors.length === 0 ? (
                        <div className="text-center py-10 text-muted-foreground">
                            No sensors found. Please configure a sensor first.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Sensor Name</TableHead>
                                    <TableHead>Location</TableHead>
                                    <TableHead>Source Type</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {sensors.map((sensor) => (
                                    <TableRow key={sensor.id}>
                                        <TableCell className="font-medium">{sensor.name}</TableCell>
                                        <TableCell>{sensor.location}</TableCell>
                                        <TableCell>
                                            <Badge variant="secondary" className="font-normal">
                                                {sensor.source_type}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <span className={`h-2.5 w-2.5 rounded-full ${sensor.latest_status === 'Normal' ? 'bg-green-500' :
                                                    sensor.latest_status === 'Warning' ? 'bg-yellow-500' :
                                                        sensor.latest_status === 'Critical' ? 'bg-red-500' :
                                                            'bg-gray-400'
                                                    }`} />
                                                <span className="text-sm text-muted-foreground">
                                                    {sensor.latest_status || 'Unknown'}
                                                </span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex justify-end items-center gap-2">
                                                <DataUploadModal
                                                    sensorId={sensor.id}
                                                    onUploadSuccess={fetchSensors}
                                                />
                                                <DeleteSensorModal
                                                    sensorId={sensor.id}
                                                    sensorName={sensor.name}
                                                    onSuccess={fetchSensors}
                                                />
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
