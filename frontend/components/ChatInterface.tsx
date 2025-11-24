"use client";

import { useState, useRef, useEffect } from "react";
import { ArrowUp, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import ReactMarkdown from "react-markdown";
import { Spinner } from "@/components/ui/spinner";

const TEXT_DISPLAY_DELAY = 30; // Delay in ms for text display

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatInterfaceProps {
  toggleSidebar: () => void;
}

export function ChatInterface({ toggleSidebar }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm Jasper. How can I help you today?",
      role: "assistant",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Create session on mount
  useEffect(() => {
    const createSession = async () => {
      try {
        const response = await fetch(`${API_URL}/chat/sessions`, {
          method: "POST",
        });

        if (!response.ok) {
          throw new Error("Failed to create session");
        }

        const data = await response.json();
        setSessionId(data.session_id);
        console.log("Session created:", data.session_id);
      } catch (error) {
        console.error("Error creating session:", error);
      }
    };

    createSession();
  }, []);

  interface MessagePayload {
    content: string;
    type: "ai" | "user"; // Assuming 'user' might exist based on 'ai'
    session_id: string;
  }

  interface ServerResponse {
    event: string;
    data: MessagePayload;
  }

  function parseFastAPIResponse(responseString: string): MessagePayload | null {
    try {
      // Remove the "data: " prefix
      // We trim to handle potential accidental whitespace
      const cleanJson = responseString.replace("data: ", "").trim();

      // Parse the string into a JSON object
      const parsedObj: ServerResponse = JSON.parse(cleanJson);

      // Return just the inner data content you need
      return parsedObj.data;
    } catch (error) {
      console.error("Failed to parse response:", error);
      return null;
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = "auto";

      // Calculate new height with a maximum limit
      const maxHeight = 150; // Maximum height in pixels (approximately 5-6 lines)
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight);

      textareaRef.current.style.height = newHeight + "px";

      // Enable overflow scrolling if content exceeds max height
      textareaRef.current.style.overflowY =
        textareaRef.current.scrollHeight > maxHeight ? "auto" : "hidden";
    }
  }, [input]);

  const streamResponse = async (messageContent: string) => {
    // Wait for session to be created
    if (!sessionId) {
      console.error("No session ID available");
      return;
    }

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      content: "",
      role: "assistant",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsWaitingForResponse(true);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: messageContent,
          session_id: sessionId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Failed to get response reader");
      }

      let buffer = "";
      let textQueue = ""; // Queue for text to be displayed
      let isDisplaying = false;
      let firstChunkReceived = false;

      // Function to display queued text with delay
      const displayQueuedText = async () => {
        if (isDisplaying) return;
        isDisplaying = true;

        while (textQueue.length > 0) {
          // Take 1-3 characters at a time for a natural feel
          const chunkSize = Math.min(
            Math.floor(Math.random() * 3) + 1,
            textQueue.length
          );
          const chunk = textQueue.slice(0, chunkSize);
          textQueue = textQueue.slice(chunkSize);

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );

          await new Promise((resolve) =>
            setTimeout(resolve, TEXT_DISPLAY_DELAY)
          );
        }

        isDisplaying = false;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // Make sure all queued text is displayed before finishing
          while (textQueue.length > 0) {
            await new Promise((resolve) => setTimeout(resolve, 10));
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          // Trim whitespace
          const trimmedLine = line.trim();

          // Skip empty lines
          if (!trimmedLine) {
            continue;
          }

          // Parse SSE format: "data: {json}"
          if (trimmedLine.startsWith("data:")) {
            const dataStr = trimmedLine.slice(5).trim();

            // Skip if no data after "data:"
            if (!dataStr) {
              continue;
            }

            try {
              // Parse the SSE event
              // console.log(dataStr)
              const eventData = parseFastAPIResponse(dataStr);

              if (!eventData) {
                continue;
              }

              if (typeof eventData.content === "string") {
                textQueue += eventData.content;
                displayQueuedText();
              }
              break;
            } catch (parseError) {
              console.error("Error parsing SSE data:", parseError);
              console.error("Problematic data:", dataStr);
              // Continue processing other lines instead of breaking
            }
          }
        }
      }
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        console.log("Request aborted");
      } else {
        console.error("Error streaming response:", error);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content:
                    msg.content ||
                    "Sorry, I encountered an error. Please try again.",
                }
              : msg
          )
        );
      }
    } finally {
      setIsStreaming(false);
      setIsWaitingForResponse(false);
      abortControllerRef.current = null;
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming || isWaitingForResponse || !sessionId)
      return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput("");
    setIsStreaming(true);

    await streamResponse(userInput);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen flex-col bg-white dark:bg-zinc-900">
      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-8">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`mb-8 ${
                message.role === "user" ? "ml-auto max-w-2xl" : ""
              }`}
            >
              <div className="mb-2 flex items-center gap-2">
                {message.role === "assistant" ? (
                  <Badge className="bg-secondary text-secondary-foreground font-bold border-2 border-black">
                    RoutAI
                  </Badge>
                ) : (
                  <Badge className="bg-primary text-secondary-foreground font-bold border-2 border-black">
                    You
                  </Badge>
                )}
              </div>
              <div className="pl-8">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isWaitingForResponse && (
            <div className="pl-8">
              <Spinner />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="py-5">
        <div className="mx-auto max-w-3xl px-4 py-2">
          <div className="relative flex items-center gap-2 px-4 py-2">
            <Button
              size="icon"
              onClick={toggleSidebar}
              variant="secondary"
              className="shrink-0 border-2 border-black"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInput(e.target.value)
              }
              onKeyDown={handleKeyPress}
              placeholder="Ask me a question..."
              rows={1}
              className="px-4 py-2 w-full border-2 border-black shadow-md transition focus:outline-hidden focus:shadow-xs"
              disabled={!sessionId}
            />
            <Button
              size="icon"
              onClick={handleSend}
              disabled={
                !input.trim() ||
                isStreaming ||
                isWaitingForResponse ||
                !sessionId
              }
              className="shadow-md hover:shadow active:shadow-none bg-primary shadow-secondary text-secondary-foreground border-2 border-black transition hover:translate-y-1 active:translate-y-2 active:translate-x-1 hover:bg-secondary-hover"
            >
              <ArrowUp className="w-5 h-5 text-black" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
