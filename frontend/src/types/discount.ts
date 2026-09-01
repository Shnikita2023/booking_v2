export type DiscountType = 'global' | 'event' | 'client';

export interface DiscountRead {
  id: string;
  name: string;
  percent: number;
  discount_type: DiscountType;
  event_id: string | null;
  client_id: string | null;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DiscountCreate {
  name: string;
  percent: number;
  discount_type: DiscountType;
  event_id?: string | null;
  client_id?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  is_active?: boolean;
}

export type DiscountUpdate = Partial<Omit<DiscountCreate, 'discount_type' | 'event_id' | 'client_id'>>;
