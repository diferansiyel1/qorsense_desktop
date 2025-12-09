import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogClose
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface DeleteSensorModalProps {
    sensorId: string;
    sensorName: string;
    onSuccess: () => void;
}

export function DeleteSensorModal({ sensorId, sensorName, onSuccess }: DeleteSensorModalProps) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();

    const handleDelete = async () => {
        setLoading(true);
        try {
            await api.sensors.delete(sensorId);
            toast({
                title: "Sensor deleted",
                description: `Successfully deleted ${sensorName}`,
            });
            setOpen(false);
            onSuccess();
        } catch (error: any) {
            toast({
                variant: "destructive",
                title: "Deletion failed",
                description: error.message || "Could not delete sensor",
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive/90 hover:bg-destructive/10">
                    <Trash2 className="h-4 w-4" />
                    <span className="sr-only">Delete</span>
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Delete Sensor?</DialogTitle>
                    <DialogDescription>
                        This action cannot be undone. This will permanently delete the sensor
                        <span className="font-semibold text-foreground"> {sensorName} </span>
                        and remove all associated data and analysis history from our servers.
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter className="gap-2 sm:gap-0">
                    <DialogClose asChild>
                        <Button variant="outline" disabled={loading}>Cancel</Button>
                    </DialogClose>
                    <Button
                        variant="destructive"
                        onClick={handleDelete}
                        disabled={loading}
                    >
                        {loading ? "Deleting..." : "Delete Sensor"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
