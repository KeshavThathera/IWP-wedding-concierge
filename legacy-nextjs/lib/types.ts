export type Department = "Wedding Sales" | "Client Servicing" | "HR and Careers" | "Vendors and Partnerships" | "Marketing and PR" | "Finance" | "General Support";
export type ConversationStatus = "Open" | "Waiting" | "Resolved";
export type LeadStage = "New" | "Qualified" | "Contacted" | "Consultation booked" | "Proposal sent" | "Converted";

export type Message = { id: string; role: "visitor" | "assistant" | "agent"; text: string; at: string };
export type Conversation = {
  id: string; ticket: string; customer: string; department: Department; status: ConversationStatus;
  priority: "Low" | "Medium" | "High"; latest: string; summary: string; updatedAt: string;
  assignedTo?: string; note?: string; transcript: Message[];
};
export type Lead = {
  id: string; name: string; contact: string; destination: string; guests: number; budget: string;
  date: string; venueStyle: string; contactMethod: string; stage: LeadStage; score: number; createdAt: string;
};
