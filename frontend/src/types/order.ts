export type OrderStatus = 'reserved' | 'paid' | 'cancelled' | 'refunded';

export interface TicketRead {
  id: string;
  ticket_type_id: string;
  price: string;
  status: string;
}

export interface OrderRead {
  id: string;
  event_id: string;
  client_id?: string | null;
  status: OrderStatus;
  total_amount: string;
  reserved_until: string | null;
  created_at: string;
  tickets: TicketRead[];
}

export interface OrderItemRequest {
  ticket_type_id: string;
  quantity: number;
}

export interface OrderCreateRequest {
  event_id: string;
  items: OrderItemRequest[];
}
