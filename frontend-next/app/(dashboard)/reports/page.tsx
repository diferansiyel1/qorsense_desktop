import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FileText } from "lucide-react";

export default function ReportsPage() {
    return (
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
            <Card className="w-full max-w-md text-center border-dashed bg-card/50">
                <CardHeader className="flex flex-col items-center">
                    <div className="p-4 rounded-full bg-primary/10 mb-4">
                        <FileText className="w-8 h-8 text-primary" />
                    </div>
                    <CardTitle className="text-2xl">Reports Archive</CardTitle>
                    <CardDescription>View and download past reports.</CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">This module is under construction.</p>
                </CardContent>
            </Card>
        </div>
    );
}
