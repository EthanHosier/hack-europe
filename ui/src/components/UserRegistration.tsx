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
import { useRegisterUserUsersRegisterPost } from "@/api/generated/endpoints";

interface UserRegistrationProps {
  onRegistered: (userId: string, role: "Victim" | "Responder" | "Admin", name: string) => void;
}

export function UserRegistration({ onRegistered }: UserRegistrationProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<"Victim" | "Responder" | "Admin" | null>(null);
  const [location, setLocation] = useState("");

  const registerUser = useRegisterUserUsersRegisterPost();

  const handleRegister = async () => {
    if (!name.trim() || !phone.trim() || !role) return;

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

      const result = await registerUser.mutateAsync({
        data: {
          name,
          phone,
          role,
          location: location || undefined,
          latitude,
          longitude,
        }
      });

      if (result.data) {
        onRegistered(result.data.id, role, name);
      }
    } catch (error) {
      console.error("Registration failed:", error);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-gray-100">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Hermes Emergency Response System</CardTitle>
          <CardDescription>
            Register to access the disaster response network
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Your Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              className="w-full mt-1 p-2 rounded-md border"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Phone Number</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Enter your phone number"
              className="w-full mt-1 p-2 rounded-md border"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Location (optional)</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., Downtown Seattle"
              className="w-full mt-1 p-2 rounded-md border"
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Select Your Role</label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant={role === "Victim" ? "default" : "outline"}
                onClick={() => setRole("Victim")}
                className="h-24 flex flex-col gap-2"
              >
                <span className="text-2xl">🆘</span>
                <span>I Need Help</span>
                <span className="text-xs opacity-70">Request emergency assistance</span>
              </Button>
              <Button
                variant={role === "Responder" ? "default" : "outline"}
                onClick={() => setRole("Responder")}
                className="h-24 flex flex-col gap-2"
              >
                <span className="text-2xl">🦸</span>
                <span>I Can Help</span>
                <span className="text-xs opacity-70">Respond to emergencies</span>
              </Button>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            className="w-full"
            onClick={handleRegister}
            disabled={!name.trim() || !phone.trim() || !role || registerUser.isPending}
          >
            {registerUser.isPending ? "Registering..." : "Register & Continue"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}