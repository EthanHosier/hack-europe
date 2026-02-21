import {
  useDbHealthDbHealthGet,
  useHealthcheckHealthGet,
  useReadRootGet,
} from "@/api/generated/endpoints";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function App() {
  const { data, isLoading, error, refetch } = useReadRootGet();
  const health = useHealthcheckHealthGet();
  const dbHealth = useDbHealthDbHealthGet();

  return (
    <div className="flex flex-col items-center justify-center min-h-svh gap-4 p-4">
      <h1 className="text-2xl font-semibold">HackEurope!</h1>
      <Button onClick={() => refetch()}>Click me</Button>
      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {error ? (
        <p className="text-destructive">
          Error: {error instanceof Error ? error.message : String(error)}
        </p>
      ) : null}
      {data?.data && (
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{data.data.Python}</CardTitle>
            <CardDescription>{data.data.message}</CardDescription>
          </CardHeader>
        </Card>
      )}
      {health.data?.data && (
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Health</CardTitle>
            <CardDescription>
              {health.data.data.status} · v{health.data.data.version}
            </CardDescription>
          </CardHeader>
        </Card>
      )}
      {dbHealth.data?.data && (
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Database</CardTitle>
            <CardDescription>
              {dbHealth.data.data.connected ? "Connected" : "Disconnected"}
            </CardDescription>
          </CardHeader>
        </Card>
      )}
      {dbHealth.isError && (
        <Card className="w-full max-w-md border-destructive">
          <CardHeader>
            <CardTitle>Database</CardTitle>
            <CardDescription>
              Error:{" "}
              {dbHealth.error instanceof Error
                ? dbHealth.error.message
                : String(dbHealth.error)}
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}

export default App;
