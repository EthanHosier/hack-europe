import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useRegisterUserUsersRegisterPost,
  useCreateEmergencyEmergencyPost,
  useRespondToCaseCasesCaseIdRespondPost,
} from "@/api/generated/endpoints";

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
  timestamp: Date;
}

interface UserState {
  id?: string;
  name?: string;
  phone?: string;
  role?: "Victim" | "Responder" | "Admin";
  currentCase?: string;
  availableCases?: any[];
}

export function TextChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [userState, setUserState] = useState<UserState>({});
  const [conversationState, setConversationState] = useState<
    | "greeting"
    | "getName"
    | "getPhone"
    | "getRole"
    | "confirmRegistration"
    | "registered"
    | "awaitingHelp"
    | "helping"
    | "inEmergency"
  >("greeting");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const registerUser = useRegisterUserUsersRegisterPost();
  const createEmergency = useCreateEmergencyEmergencyPost();
  const respondToCase = useRespondToCaseCasesCaseIdRespondPost();

  useEffect(() => {
    // Initial greeting
    addSystemMessage(
      "Hello! I'm the Hermes Emergency Response System. I'm here to help connect people in need with those who can help during disasters. What's your name?"
    );
    setConversationState("getName");
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addSystemMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        text,
        sender: "system",
        timestamp: new Date(),
      },
    ]);
  };

  const addUserMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        text,
        sender: "user",
        timestamp: new Date(),
      },
    ]);
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userInput = input.trim();
    addUserMessage(userInput);
    setInput("");

    // Process based on conversation state
    switch (conversationState) {
      case "getName":
        setUserState((prev) => ({ ...prev, name: userInput }));
        addSystemMessage(
          `Nice to meet you, ${userInput}! What's your phone number? This will be used to connect you with help or those who need help.`
        );
        setConversationState("getPhone");
        break;

      case "getPhone":
        setUserState((prev) => ({ ...prev, phone: userInput }));
        addSystemMessage(
          `Thank you! Now, I need to understand your situation. Are you:\n` +
            `1. Someone who needs help (victim of a disaster)\n` +
            `2. Someone who can provide help (responder)\n` +
            `3. An administrator\n\n` +
            `Please type 1, 2, or 3, or describe your situation.`
        );
        setConversationState("getRole");
        break;

      case "getRole":
        let role: "Victim" | "Responder" | "Admin" | undefined;
        const lowerInput = userInput.toLowerCase();

        if (
          lowerInput === "1" ||
          lowerInput.includes("need help") ||
          lowerInput.includes("victim") ||
          lowerInput.includes("emergency") ||
          lowerInput.includes("stuck") ||
          lowerInput.includes("stranded")
        ) {
          role = "Victim";
        } else if (
          lowerInput === "2" ||
          lowerInput.includes("can help") ||
          lowerInput.includes("responder") ||
          lowerInput.includes("volunteer") ||
          lowerInput.includes("assist")
        ) {
          role = "Responder";
        } else if (lowerInput === "3" || lowerInput.includes("admin")) {
          role = "Admin";
        }

        if (role) {
          setUserState((prev) => ({ ...prev, role }));
          const roleText =
            role === "Victim"
              ? "someone who needs help"
              : role === "Responder"
              ? "a responder who can help others"
              : "an administrator";
          addSystemMessage(
            `I understand you're ${roleText}. Let me register you in the system.\n\n` +
              `Name: ${userState.name}\n` +
              `Phone: ${userState.phone}\n` +
              `Role: ${roleText}\n\n` +
              `Is this correct? (yes/no)`
          );
          setConversationState("confirmRegistration");
        } else {
          addSystemMessage(
            "I didn't quite understand. Please type:\n" +
              "1 if you need help\n" +
              "2 if you can provide help\n" +
              "3 if you're an administrator"
          );
        }
        break;

      case "confirmRegistration":
        if (userInput.toLowerCase().includes("yes")) {
          // Register the user
          try {
            const result = await registerUser.mutateAsync({
              data: {
                name: userState.name!,
                phone: userState.phone!,
                role: userState.role!,
              },
            });

            if (result.data) {
              setUserState((prev) => ({ ...prev, id: result.data.id }));
              localStorage.setItem("hermesUserId", result.data.id);
              localStorage.setItem("hermesUserRole", userState.role!);
              localStorage.setItem("hermesUserName", userState.name!);

              if (userState.role === "Victim") {
                addSystemMessage(
                  "You're now registered! If you have an emergency, please describe your situation. " +
                    "For example: 'Out of fuel on Highway 95' or 'Need medical help, injured leg'. " +
                    "I'll connect you with someone who can help."
                );
                setConversationState("registered");
              } else if (userState.role === "Responder") {
                addSystemMessage(
                  "Thank you for volunteering to help! I'll show you any emergency cases that need assistance. " +
                    "Type 'check' to see if anyone needs help, or wait for notifications."
                );
                setConversationState("registered");
              } else {
                addSystemMessage(
                  "You're registered as an administrator. Type 'status' to see system status."
                );
                setConversationState("registered");
              }
            }
          } catch (error) {
            addSystemMessage(
              "There was an error registering you. Please try again or refresh the page."
            );
          }
        } else {
          addSystemMessage("Let's start over. What's your name?");
          setUserState({});
          setConversationState("getName");
        }
        break;

      case "registered":
      case "awaitingHelp":
      case "helping":
        await handleRegisteredUserInput(userInput);
        break;
    }
  };

  const handleRegisteredUserInput = async (input: string) => {
    const lowerInput = input.toLowerCase();

    if (userState.role === "Victim") {
      // Check if this is an emergency message
      const emergencyKeywords = [
        "help",
        "emergency",
        "stuck",
        "stranded",
        "fuel",
        "injured",
        "hurt",
        "cold",
        "freezing",
        "hungry",
        "thirsty",
        "trapped",
        "lost",
      ];

      if (emergencyKeywords.some((keyword) => lowerInput.includes(keyword))) {
        try {
          addSystemMessage(
            "I understand this is an emergency. Let me create an emergency case for you..."
          );

          const result = await createEmergency.mutateAsync(
            {
              data: {
                message: input,
              },
            },
            {
              //@ts-ignore
              request: {
                headers: {
                  "X-User-Id": userState.id!,
                },
              },
            }
          );

          if (result.data) {
            setUserState((prev) => ({ ...prev, currentCase: result.data.id }));
            addSystemMessage(
              `Emergency case created!\n` +
                `Category: ${result.data.category?.replace("_", " ")}\n` +
                `Severity: ${result.data.severity}/5\n` +
                `Status: ${result.data.status}\n\n` +
                `I'm broadcasting your emergency to nearby helpers. Someone should respond soon. ` +
                `You can type messages here and they'll be shared with your helper when they arrive.`
            );
            setConversationState("awaitingHelp");
          }
        } catch (error) {
          addSystemMessage(
            "I couldn't create the emergency case. Please try describing your emergency again."
          );
        }
      } else {
        addSystemMessage(
          "I'm here to help with emergencies. If you need help, please describe your emergency situation. " +
            "For example: 'Out of fuel', 'Injured and need medical help', 'Stranded in blizzard'."
        );
      }
    } else if (userState.role === "Responder") {
      if (
        lowerInput.includes("check") ||
        lowerInput.includes("help") ||
        lowerInput.includes("cases")
      ) {
        try {
          // Fetch cases directly using the API
          const response = await fetch("/api/cases?role=Responder", {
            headers: {
              "X-User-Id": userState.id!,
            },
          });

          if (response.ok) {
            const cases = await response.json();

            if (cases && cases.length > 0) {
              let caseList = "Here are the current emergency cases:\n\n";
              cases.forEach((c: any, index: number) => {
                caseList += `${index + 1}. ${c.title || c.category} - ${
                  c.summary
                }\n`;
                caseList += `   Severity: ${c.severity}/5, Status: ${c.status}\n\n`;
              });
              caseList += "Type the number of the case you want to help with.";
              addSystemMessage(caseList);

              // Store cases in state for reference
              setUserState((prev) => ({ ...prev, availableCases: cases }));
            } else {
              addSystemMessage(
                "No emergency cases at the moment. I'll notify you when someone needs help."
              );
            }
          } else {
            addSystemMessage("Couldn't fetch cases. Please try again.");
          }
        } catch (error) {
          addSystemMessage("Couldn't fetch cases. Please try again.");
        }
      } else if (/^\d+$/.test(lowerInput) && userState.availableCases) {
        const caseIndex = parseInt(lowerInput) - 1;
        if (caseIndex >= 0 && caseIndex < userState.availableCases.length) {
          const selectedCase = userState.availableCases[caseIndex];
          try {
            await respondToCase.mutateAsync(
              {
                caseId: selectedCase.id,
                data: {
                  message: "I can help with this emergency",
                },
              },
              {
                //@ts-ignore
                request: {
                  headers: {
                    "X-User-Id": userState.id!,
                  },
                },
              }
            );

            setUserState((prev) => ({ ...prev, currentCase: selectedCase.id }));
            addSystemMessage(
              `You're now responding to: ${selectedCase.summary}\n\n` +
                `You can communicate with the person in need through this chat. ` +
                `Type your messages here to coordinate assistance.`
            );
            setConversationState("helping");
          } catch (error) {
            addSystemMessage(
              "Couldn't assign you to this case. Please try again."
            );
          }
        } else {
          addSystemMessage(
            "Invalid case number. Please type 'check' to see available cases."
          );
        }
      } else {
        addSystemMessage("Type 'check' to see emergency cases that need help.");
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-screen max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Hermes Emergency Response System</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col h-[calc(100vh-100px)]">
        <div className="flex-1 overflow-y-auto space-y-2 mb-4 p-4 border rounded">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.sender === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  msg.sender === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <div className="text-xs opacity-70 mb-1">
                  {msg.sender === "user" ? "You" : "System"} •{" "}
                  {msg.timestamp.toLocaleTimeString()}
                </div>
                <div className="whitespace-pre-wrap">{msg.text}</div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 p-2 border rounded"
            autoFocus
          />
          <Button onClick={handleSend}>Send</Button>
        </div>
      </CardContent>
    </Card>
  );
}
