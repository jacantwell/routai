"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import RoutePlannerMap from "@/components/RoutePlannerMap";

interface RouteModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function RouteModal({ sessionId, isOpen, onClose }: RouteModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative z-10 w-full h-full max-w-7xl max-h-[90vh] m-4 bg-white dark:bg-zinc-900 rounded-lg shadow-xl border-2 border-black flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b-2 border-black">
          <h2 className="text-xl font-bold">Your Route</h2>
          <Button
            size="icon"
            variant="ghost"
            onClick={onClose}
            className="hover:bg-secondary"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        {/* Map Container */}
        <div className="flex-1 overflow-hidden p-4">
          <RoutePlannerMap 
            sessionId={sessionId} 
            className="w-full h-full rounded-lg border-2 border-black"
          />
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t-2 border-black">
          <p className="text-sm text-muted-foreground text-center">
            Close this modal to continue chatting and refine your route
          </p>
        </div>
      </div>
    </div>
  );
}