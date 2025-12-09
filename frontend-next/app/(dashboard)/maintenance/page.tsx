"use client";

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { CalendarClock, CheckCircle, AlertCircle, Clock, Plus, Filter, Wrench } from "lucide-react";
import { CreateMaintenanceModal } from "@/components/CreateMaintenanceModal";

// Mock Data
const MOCK_TASKS = [
    { id: 1, sensor: "Bioreactor pH Probe 01", type: "Calibration", dueDate: "2025-12-10", priority: "High", status: "Pending", sensorId: "1" },
    { id: 2, sensor: "DO Probe @ Mix Tank", type: "Cleaning", dueDate: "2025-12-05", priority: "Normal", status: "Overdue", sensorId: "2" },
    { id: 3, sensor: "Main Line Flowmeter", type: "Inspection", dueDate: "2025-12-08", priority: "Normal", status: "Pending", sensorId: "3" },
    { id: 4, sensor: "Bioreactor pH Probe 01", type: "Replacement", dueDate: "2025-11-20", priority: "Critical", status: "Completed", sensorId: "1" },
    { id: 5, sensor: "Pressure TX-101", type: "Calibration", dueDate: "2025-12-15", priority: "Normal", status: "Pending", sensorId: "4" },
];

function MaintenanceContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const sensorIdParam = searchParams.get('sensorId');
    const actionParam = searchParams.get('action');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [allTasks, setAllTasks] = useState(MOCK_TASKS);
    const [filteredTasks, setFilteredTasks] = useState(MOCK_TASKS);
    const [editingTask, setEditingTask] = useState<any>(null);

    useEffect(() => {
        let tasks = allTasks;
        if (sensorIdParam) {
            tasks = tasks.filter(t => t.sensorId === sensorIdParam || t.sensor.includes(sensorIdParam));
        }
        setFilteredTasks(tasks);

        if (actionParam === 'new') {
            setEditingTask(null);
            setIsModalOpen(true);
        }
    }, [sensorIdParam, actionParam, allTasks]);

    const handleCloseModal = () => {
        setIsModalOpen(false);
        setEditingTask(null);
        if (actionParam) {
            router.push('/maintenance');
        }
    };

    const handleCreateOrUpdateTask = (task: any) => {
        setAllTasks(prev => {
            const exists = prev.find(t => t.id === task.id);
            if (exists) {
                return prev.map(t => t.id === task.id ? task : t);
            }
            // For new tasks, assign a temporary ID. In a real app, this would come from the backend.
            const newId = Math.max(...prev.map(t => t.id)) + 1;
            return [{ ...task, id: newId }, ...prev];
        });
    };

    const handleEditClick = (task: any) => {
        setEditingTask(task);
        setIsModalOpen(true);
    };

    const getStatusVariant = (status: string) => {
        switch (status) {
            case 'Overdue': return 'destructive'; // Red
            case 'Pending': return 'secondary';   // Yellow-ish/Grey
            case 'Completed': return 'outline';   // Green/Outline
            default: return 'secondary';
        }
    };

    // Calculate KPIs from allTasks (or filtered? usually KPIs are global or filtered context)
    // Let's use filtered for context sensitive KPIs, or all for global. Dashboard usually global.
    // Let's stick to global for the top cards unless filtered is active? 
    // Standard dashboard behavior: Top cards global, list filtered.
    const pendingCount = allTasks.filter(t => t.status === 'Pending').length;
    const overdueCount = allTasks.filter(t => t.status === 'Overdue').length;
    const completedCount = allTasks.filter(t => t.status === 'Completed').length;

    return (
        <div className="min-h-screen bg-background p-8 space-y-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Maintenance Operations Center</h1>
                    <p className="text-muted-foreground mt-1">Manage, schedule, and track all sensor maintenance activities.</p>
                </div>
                <Button onClick={() => { setEditingTask(null); setIsModalOpen(true); }} className="bg-primary text-white hover:bg-primary/90">
                    <Plus className="w-4 h-4 mr-2" /> New Task
                </Button>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-l-4 border-l-status-yellow bg-card/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending Tasks</CardTitle>
                        <Clock className="h-4 w-4 text-status-yellow" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{pendingCount}</div>
                        <p className="text-xs text-muted-foreground">Tasks waiting for action</p>
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-status-red bg-card/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Overdue</CardTitle>
                        <AlertCircle className="h-4 w-4 text-status-red" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{overdueCount}</div>
                        <p className="text-xs text-muted-foreground">High priority attention needed</p>
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-status-green bg-card/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Completed (Month)</CardTitle>
                        <CheckCircle className="h-4 w-4 text-status-green" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{completedCount}</div>
                        <p className="text-xs text-muted-foreground">Maintenance efficiency on track</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content Area */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Maintenance Schedule</CardTitle>
                            <CardDescription>
                                {sensorIdParam ? `Showing tasks for Sensor ID: ${sensorIdParam}` : "All active maintenance tasks"}
                            </CardDescription>
                        </div>
                        {sensorIdParam && (
                            <Button variant="ghost" size="sm" onClick={() => router.push('/maintenance')}>
                                Clear Filter <Filter className="w-3 h-3 ml-2" />
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[120px]">Due Date</TableHead>
                                <TableHead>Sensor</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Priority</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredTasks.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                                        No tasks found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredTasks.map((task) => (
                                    <TableRow key={task.id}>
                                        <TableCell className="font-medium">{task.dueDate}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span className="font-semibold">{task.sensor}</span>
                                                <span className="text-xs text-muted-foreground">ID: {task.sensorId}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <Wrench className="w-3 h-3 text-muted-foreground" />
                                                {task.type}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={task.priority === 'High' || task.priority === 'Critical' ? 'destructive' : 'secondary'}>
                                                {task.priority}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={getStatusVariant(task.status) as any} className={task.status === 'Completed' ? 'text-status-green border-status-green' : ''}>
                                                {task.status}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button variant="ghost" size="sm" onClick={() => handleEditClick(task)}>Edit</Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <CreateMaintenanceModal
                isOpen={isModalOpen}
                onClose={handleCloseModal}
                defaultSensorId={sensorIdParam}
                onCreate={handleCreateOrUpdateTask}
                initialData={editingTask}
            />
        </div>
    );
}

export default function MaintenancePage() {
    return (
        <Suspense fallback={<div className="p-8">Loading...</div>}>
            <MaintenanceContent />
        </Suspense>
    );
}

