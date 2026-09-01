export type EventStatus = 'draft' | 'on_sale' | 'paused' | 'cancelled' | 'completed' | 'moved';

export interface EventRead {
  id: string;
  title: string;
  description: string | null;
  starts_at: string;
  duration_min: number | null;
  age_rating: string | null;
  venue: string | null;
  price: string | null;
  status: EventStatus;
  banner_small_url: string | null;
  banner_large_url: string | null;
  show_free_tickets: boolean;
  sale_paused: boolean;
  cloned_from_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface TicketTypeSeed {
  name: string;
  price: number;
  quota: number;
}

export interface EventCreate {
  title: string;
  description?: string | null;
  starts_at: string;
  duration_min?: number | null;
  age_rating?: string | null;
  venue?: string | null;
  banner_small_url?: string | null;
  banner_large_url?: string | null;
  show_free_tickets?: boolean;
  sale_paused?: boolean;
  ticket_types?: TicketTypeSeed[] | null;
}

export type EventUpdate = Partial<EventCreate>;

export interface EventMove {
  starts_at: string;
}

export interface TicketTypeRead {
  id: string;
  event_id: string;
  name: string;
  price: string;
  quota: number;
  sold: number;
  deleted_at: string | null;
}

export interface TicketTypeCreate {
  name: string;
  price: number;
  quota: number;
}

export type TicketTypeUpdate = Partial<TicketTypeCreate>;
