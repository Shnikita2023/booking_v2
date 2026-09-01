export type PaymentStatus = 'pending' | 'succeeded' | 'failed' | 'refunded';

export interface PaymentRead {
  id: string;
  order_id: string;
  status: PaymentStatus;
  amount: string;
  external_id: string | null;
  method: string | null;
  currency: string | null;
  gateway: string | null;
  paid_at: string | null;
  created_at: string;
}
