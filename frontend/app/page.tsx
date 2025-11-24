"use client";

import { useState } from "react";
import { ChatInterface } from "@/components/ChatInterface";
// import { Sidebar } from "@/components/Sidebar";

export default function Home() {
  const [isOpen, setIsOpen] = useState(false);

  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <>
      <ChatInterface toggleSidebar={toggleSidebar} />
    </>
  );
}
