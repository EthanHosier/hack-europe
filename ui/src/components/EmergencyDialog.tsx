import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useCreateEmergencyEmergencyPost } from "@/api/generated/endpoints";

interface EmergencyDialogProps {
  userId: string;
  onEmergencyCreated: (caseId: string) => void;
}

export function EmergencyDialog({ userId, onEmergencyCreated }: EmergencyDialogProps) {
  const [message, setMessage] = useState("");
  const [location, setLocation] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const createEmergency = useCreateEmergencyEmergencyPost();

  const handleSubmit = async () => {
    if (!message.trim()) return;

    try {
      // Get current location if available
      let latitude: number | undefined;
      let longitude: number | undefined;

      if (navigator.geolocation) {
        try {
          const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
          });
          latitude = position.coords.latitude;
          longitude = position.coords.longitude;
        } catch (err) {
          console.warn("Could not get location:", err);
        }
      }

      const result = await createEmergency.mutateAsync({
        data: {
          message,
          location: location || undefined,
          latitude,
          longitude,
        }
      }, {
        request: {
          headers: {
            "X-User-Id": userId,
          }
        }
      });

      if (result.data) {
        onEmergencyCreated(result.data.id);
        setMessage("");
        setLocation("");
        setIsOpen(false);
      }
    } catch (error) {
      console.error("Failed to create emergency:", error);
    }
  };

  if (!isOpen) {
    return (
      <Button
        size="lg"
        variant="destructive"
        onClick={() => setIsOpen(true)}
        className="w-full"
      >
        🚨 EMERGENCY - Request Help
      </Button>
    );
  }

  return (
    <Card className="border-destructive">
      <CardHeader>
        <CardTitle className="text-destructive">Emergency Request</CardTitle>
        <CardDescription>
          Describe your emergency. Help will be dispatched as soon as possible.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">What's your emergency?</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="e.g., Out of fuel on Highway 95, blizzard conditions..."
            className="w-full mt-1 p-2 rounded-md border min-h-[100px]"
            autoFocus
          />
        </div>
        <div>
          <label className="text-sm font-medium">Location (optional)</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g., Highway 95 near mile marker 42"
            className="w-full mt-1 p-2 rounded-md border"
          />
        </div>
        <div className="text-sm text-muted-foreground">
          We'll try to get your GPS location automatically when you submit.
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button variant="outline" onClick={() => setIsOpen(false)}>
          Cancel
        </Button>
        <Button
          variant="destructive"
          onClick={handleSubmit}
          disabled={!message.trim() || createEmergency.isPending}
        >
          {createEmergency.isPending ? "Sending..." : "Send Emergency Request"}
        </Button>
      </CardFooter>
    </Card>
  );
}