import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useGetCasesCasesGet, useRespondToCaseCasesCaseIdRespondPost } from "@/api/generated/endpoints";

interface CaseListProps {
  userId: string;
  role: "Victim" | "Responder" | "Admin";
  onSelectCase: (caseId: string) => void;
}

export function CaseList({ userId, role, onSelectCase }: CaseListProps) {
  const { data: casesData, refetch } = useGetCasesCasesGet(
    { role },
    {
      request: {
        headers: {
          "X-User-Id": userId,
        }
      },
      query: {
        refetchInterval: 5000, // Poll every 5 seconds for updates
      }
    }
  );

  const respondToCase = useRespondToCaseCasesCaseIdRespondPost();

  const cases = casesData?.data || [];

  const handleRespond = async (caseId: string) => {
    try {
      await respondToCase.mutateAsync({
        caseId: caseId,
        data: {
          message: "I can help with this emergency",
        }
      }, {
        request: {
          headers: {
            "X-User-Id": userId,
          }
        }
      });
      refetch();
      onSelectCase(caseId);
    } catch (error) {
      console.error("Failed to respond to case:", error);
    }
  };

  const getCategoryEmoji = (category: string | null) => {
    switch (category) {
      case 'fuel': return '⛽';
      case 'medical': return '🏥';
      case 'shelter': return '🏠';
      case 'food_water': return '🍞';
      case 'rescue': return '🆘';
      default: return '📋';
    }
  };

  const getSeverityColor = (severity: number) => {
    if (severity >= 4) return 'text-destructive';
    if (severity >= 3) return 'text-orange-500';
    return 'text-yellow-500';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Open':
        return <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">Open</span>;
      case 'In Progress':
        return <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">In Progress</span>;
      case 'Resolved':
        return <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Resolved</span>;
      default:
        return null;
    }
  };

  if (cases.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No active cases at the moment.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">
        {role === 'Responder' ? 'Emergency Cases Needing Help' : 'Your Cases'}
      </h2>
      {cases.map((caseItem) => (
        <Card key={caseItem.id} className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-2">
                <span className="text-2xl">{getCategoryEmoji(caseItem.category)}</span>
                <div>
                  <CardTitle className="text-lg">
                    {caseItem.category ?
                      caseItem.category.charAt(0).toUpperCase() + caseItem.category.slice(1).replace('_', ' ') :
                      'Emergency'}
                  </CardTitle>
                  <CardDescription className={getSeverityColor(caseItem.severity)}>
                    Severity: {caseItem.severity}/5
                  </CardDescription>
                </div>
              </div>
              {getStatusBadge(caseItem.status)}
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-2">{caseItem.summary}</p>
            <p className="text-xs text-muted-foreground mb-4">
              Created: {new Date(caseItem.created_at).toLocaleString()}
            </p>
            <div className="flex gap-2">
              {role === 'Responder' && caseItem.status === 'Open' && (
                <Button
                  onClick={() => handleRespond(caseItem.id)}
                  disabled={respondToCase.isPending}
                >
                  Respond to Help
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => onSelectCase(caseItem.id)}
              >
                View Details
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}