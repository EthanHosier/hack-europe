import { useQueryClient } from "@tanstack/react-query";
import { useCompleteCaseCasesCaseIdCompletePost } from "@/api/generated/endpoints";
import type { LiveEventResponse } from "@/api/generated/schemas";

const LIVE_EVENTS_KEY = ["/api/events/live", { limit: 300 }] as const;

export function useCompleteCase() {
  const queryClient = useQueryClient();

  const { mutate, isPending } = useCompleteCaseCasesCaseIdCompletePost({
    mutation: {
      onMutate: async ({ caseId }) => {
        await queryClient.cancelQueries({ queryKey: ["/api/events/live"] });

        const previous = queryClient.getQueryData<{
          data: LiveEventResponse[];
        }>(LIVE_EVENTS_KEY);

        queryClient.setQueryData<{ data: LiveEventResponse[] }>(
          LIVE_EVENTS_KEY,
          (old) => {
            if (!old) return old;
            return {
              ...old,
              data: old.data.map((ev) =>
                ev.case_id === caseId
                  ? {
                      ...ev,
                      completed_at: new Date().toISOString(),
                      case_status: "Resolved",
                    }
                  : ev
              ),
            };
          }
        );

        return { previous };
      },
      onError: (_err, _vars, context) => {
        if (context?.previous) {
          queryClient.setQueryData(LIVE_EVENTS_KEY, context.previous);
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey: ["/api/events/live"] });
      },
    },
  });

  return { completeCase: mutate, isResolving: isPending };
}
