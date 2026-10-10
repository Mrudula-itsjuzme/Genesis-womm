export type EventStatus = "DRAFT" | "TENTATIVE" | "SUBMITTED" | "ACKNOWLEDGED" | "CONFIRMED";

export interface EventOut {
  id: string;
  club_id: string;
  title: string;
  description?: string;
  start_at: string;
  end_at: string;
  resource_id?: string;
  expected_attendance?: number;
  audience_tags: string[];
  status: EventStatus;
  revision: number;
  venue_availability: string;
  synthetic: boolean;
  created_at: string;
  updated_at: string;
}
