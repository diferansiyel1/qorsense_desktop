
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "lucide-react";

interface CreateMaintenanceModalProps {
    isOpen: boolean;
    onClose: () => void;
    defaultSensorId?: string | null;
    onCreate: (task: any) => void;
    initialData?: any;
}

export function CreateMaintenanceModal({
    isOpen,
    onClose,
    defaultSensorId,
    onCreate,
    initialData
}: CreateMaintenanceModalProps) {
    const [sensorId, setSensorId] = useState("");
    const [taskType, setTaskType] = useState("calibration");
    const [priority, setPriority] = useState("normal");
    const [date, setDate] = useState("");
    const [notes, setNotes] = useState("");

    useEffect(() => {
        if (initialData) {
            setSensorId(initialData.sensorId);
            // basic mapping, real app might need more robust matching
            setTaskType(initialData.type.toLowerCase());
            setPriority(initialData.priority.toLowerCase());
            setDate(initialData.dueDate);
            setNotes(initialData.notes || "");
        } else if (defaultSensorId) {
            setSensorId(defaultSensorId);
            // Reset other fields if needed when switching to create mode
            setTaskType("calibration");
            setPriority("normal");
            setDate("");
            setNotes("");
        } else {
            // Reset on plain open
            setSensorId("");
            setTaskType("calibration");
            setPriority("normal");
            setDate("");
            setNotes("");
        }
    }, [defaultSensorId, initialData, isOpen]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        const newTask = {
            id: initialData ? initialData.id : Date.now(), // Simple ID generation
            sensorId,
            sensor: sensorId === "1" ? "Bioreactor pH Probe 01" :
                sensorId === "2" ? "DO Probe @ Mix Tank" :
                    sensorId === "3" ? "Main Line Flowmeter" :
                        sensorId === "82b83144" ? "Demo Sensor (82b83144)" : sensorId,
            type: taskType.charAt(0).toUpperCase() + taskType.slice(1),
            priority: priority.charAt(0).toUpperCase() + priority.slice(1),
            dueDate: date,
            status: initialData ? initialData.status : "Pending", // Default status
            notes
        };

        onCreate(newTask);
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Schedule Maintenance</DialogTitle>
                    <DialogDescription>
                        Create a new maintenance task for a sensor.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="sensor" className="text-right">
                            Sensor
                        </Label>
                        <Select value={sensorId} onValueChange={setSensorId} disabled={!!defaultSensorId}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="Select Sensor" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="1">Bioreactor pH Probe 01</SelectItem>
                                <SelectItem value="2">DO Probe @ Mix Tank</SelectItem>
                                <SelectItem value="3">Main Line Flowmeter</SelectItem>
                                <SelectItem value="82b83144">Demo Sensor (82b83144)</SelectItem>
                                {defaultSensorId && !["1", "2", "3", "82b83144"].includes(defaultSensorId) && (
                                    <SelectItem value={defaultSensorId}>{defaultSensorId}</SelectItem>
                                )}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="type" className="text-right">
                            Task Type
                        </Label>
                        <Select value={taskType} onValueChange={setTaskType}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="Select Type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="calibration">Calibration</SelectItem>
                                <SelectItem value="replacement">Replacement</SelectItem>
                                <SelectItem value="cleaning">Cleaning</SelectItem>
                                <SelectItem value="inspection">Inspection</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="priority" className="text-right">
                            Priority
                        </Label>
                        <Select value={priority} onValueChange={setPriority}>
                            <SelectTrigger className="col-span-3">
                                <SelectValue placeholder="Select Priority" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="normal">Normal</SelectItem>
                                <SelectItem value="high">High</SelectItem>
                                <SelectItem value="critical">Critical</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="date" className="text-right">
                            Due Date
                        </Label>
                        <Input
                            id="date"
                            type="date"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="col-span-3"
                            required
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="notes" className="text-right">
                            Notes
                        </Label>
                        <Input
                            id="notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="col-span-3"
                            placeholder="Optional Details..."
                        />
                    </div>
                </form>
                <DialogFooter>
                    <Button type="submit" onClick={handleSubmit}>{initialData ? "Update Task" : "Create Task"}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
