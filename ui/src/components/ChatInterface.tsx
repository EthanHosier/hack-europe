import { useState, useEffect, useRef } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useGetCaseMessagesMessagesCaseIdGet, useSendMessageMessagesPost } from "@/api/generated/endpoints";

interface ChatInterfaceProps {
  caseId: string;
  userId: string;
  userName?: string;
}

export function ChatInterface({ caseId, userId, userName }: ChatInterfaceProps) {
  const [message, setMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: messagesData, refetch } = useGetCaseMessagesMessagesCaseIdGet(
    caseId,
    {
      query: {
        refetchInterval: 3000, // Poll every 3 seconds for new messages
      },
      request: {
        headers: {
          "X-User-Id": userId,
        }
      }
    }
  );

  const sendMessage = useSendMessageMessagesPost();

  const messages = messagesData?.data || [];

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!message.trim()) return;

    await sendMessage.mutateAsync(
      {
        data: {
          text: message,
          case_id: caseId,
          is_emergency: false,
        }
      },
      {
        request: {
          headers: {
            "X-User-Id": userId,
          }
        }
      }
    );

    setMessage("");
    refetch();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader>
        <CardTitle>Emergency Chat - Case #{caseId.slice(0, 8)}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-2">
        {messages.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No messages yet. Start the conversation...
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.user_id === userId ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  msg.user_id === userId
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <div className="text-xs opacity-70 mb-1">
                  {msg.user_name || "Unknown User"} • {new Date(msg.created_at).toLocaleTimeString()}
                </div>
                <div>{msg.text}</div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </CardContent>
      <CardFooter className="border-t">
        <div className="flex w-full gap-2">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 min-h-[40px] max-h-[120px] p-2 rounded-md border resize-none"
            rows={1}
          />
          <Button onClick={handleSend} disabled={!message.trim()}>
            Send
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}