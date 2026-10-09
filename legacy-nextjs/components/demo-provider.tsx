"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { seedConversations, seedLeads } from "@/lib/demo-data";
import { Conversation, ConversationStatus, Lead, LeadStage } from "@/lib/types";

type DemoContextValue = {
  conversations: Conversation[]; leads: Lead[]; hydrated: boolean;
  addConversation: (conversation: Conversation) => void;
  addLead: (lead: Lead) => void;
  moveLead: (id: string, stage: LeadStage) => void;
  updateConversation: (id: string, update: Partial<Pick<Conversation, "status" | "assignedTo" | "note" | "transcript" | "latest" | "updatedAt">>) => void;
  resetDemo: () => void;
};

const DemoContext = createContext<DemoContextValue | null>(null);
const STORAGE = "iwp-concierge-demo-v1";

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [conversations, setConversations] = useState(seedConversations);
  const [leads, setLeads] = useState(seedLeads);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE);
      if (stored) {
        const parsed = JSON.parse(stored) as { conversations: Conversation[]; leads: Lead[] };
        setConversations(parsed.conversations); setLeads(parsed.leads);
      }
    } catch { /* seed data is a safe fallback */ }
    setHydrated(true);
  }, []);
  useEffect(() => { if (hydrated) localStorage.setItem(STORAGE, JSON.stringify({ conversations, leads })); }, [conversations, leads, hydrated]);

  const value = useMemo(() => ({
    conversations, leads, hydrated,
    addConversation: (conversation: Conversation) => setConversations(current => [conversation, ...current.filter(c => c.id !== conversation.id)]),
    addLead: (lead: Lead) => setLeads(current => [lead, ...current.filter(l => l.id !== lead.id)]),
    moveLead: (id: string, stage: LeadStage) => setLeads(current => current.map(lead => lead.id === id ? { ...lead, stage } : lead)),
    updateConversation: (id: string, update: Partial<Pick<Conversation, "status" | "assignedTo" | "note" | "transcript" | "latest" | "updatedAt">>) => setConversations(current => current.map(item => item.id === id ? { ...item, ...update } : item)),
    resetDemo: () => { setConversations(seedConversations); setLeads(seedLeads); localStorage.removeItem(STORAGE); }
  }), [conversations, leads, hydrated]);

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) throw new Error("useDemo must be used inside DemoProvider");
  return context;
}
