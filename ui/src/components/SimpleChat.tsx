import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function SimpleChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [userId] = useState(() => {
    // Get or create a user ID
    let id = localStorage.getItem("emergencyUserId");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("emergencyUserId", id);
    }
    return id;
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial message from the system
    setMessages([{
      role: "assistant",
      content: "Hello, this is the emergency response system. I'm here to help you. Please tell me your name and describe your emergency situation."
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");

    // Add user message to chat
    const newMessages = [...messages, { role: "user" as const, content: userMessage }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      // Send to backend
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: messages,
          user_id: userId
        })
      });

      if (response.ok) {
        const data = await response.json();

        // Add AI response to chat
        setMessages([...newMessages, {
          role: "assistant",
          content: data.response
        }]);

        // If a case was created, store it
        if (data.case_id) {
          localStorage.setItem("currentCaseId", data.case_id);
        }
      } else {
        setMessages([...newMessages, {
          role: "assistant",
          content: "I'm sorry, there was an error processing your message. Please try again."
        }]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages([...newMessages, {
        role: "assistant",
        content: "I'm having trouble connecting to the emergency system. Please ensure you have a stable connection and try again."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-screen max-w-4xl mx-auto">
      <CardHeader className="border-b">
        <CardTitle>🚨 Emergency Response System</CardTitle>
        <p className="text-sm text-muted-foreground">
          Powered by AI • Available 24/7 • Your information is secure
        </p>
      </CardHeader>
      <CardContent className="flex flex-col h-[calc(100vh-120px)] p-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground ml-4'
                    : 'bg-muted mr-4'
                }`}
              >
                <div className="text-xs opacity-70 mb-1">
                  {msg.role === 'user' ? 'You' : 'Emergency Response AI'}
                </div>
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-3 mr-4">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-6"
            >
              Send
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            In case of immediate life-threatening emergency, call 911/112
          </p>
        </div>
      </CardContent>
    </Card>
  );
}