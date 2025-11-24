"use client";

import { useState } from "react";
import RoutePlannerMap from "@/components/RoutePlannerMap";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RouteVisualizerPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [inputValue, setInputValue] = useState<string>("");
  const [showMap, setShowMap] = useState(false);

  const handleLoadRoute = () => {
    if (inputValue.trim()) {
      setSessionId(inputValue.trim());
      setShowMap(true);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Route Visualizer</h1>
          <p className="text-muted-foreground">
            Enter a session ID to view your planned bikepacking route
          </p>
        </div>

        {/* Session ID Input */}
        <div className="mb-6 flex gap-2">
          <Input
            type="text"
            placeholder="Enter session ID..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleLoadRoute();
              }
            }}
            className="max-w-md"
          />
          <Button onClick={handleLoadRoute} disabled={!inputValue.trim()}>
            Load Route
          </Button>
        </div>

        {/* Map Display */}
        {showMap && sessionId && (
          <div className="mt-6">
            <RoutePlannerMap sessionId={sessionId} className="w-full" />
          </div>
        )}

        {/* Instructions */}
        {!showMap && (
          <div className="mt-8 rounded-lg border border-border bg-card p-6">
            <h2 className="text-xl font-semibold mb-3">How to use</h2>
            <ol className="space-y-2 list-decimal list-inside text-muted-foreground">
              <li>Create a route using the chat interface</li>
              <li>Copy the session ID from your conversation</li>
              <li>Paste it in the input field above</li>
              <li>Click "Load Route" to visualize your bikepacking journey</li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}