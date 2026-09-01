export interface RevenueReport {
  event_id: string;
  event_title: string;
  event_starts_at: string;
  total_revenue: string;
  payment_count: number;
}

export interface RevenueByDateReport {
  date: string;
  total_revenue: string;
  payment_count: number;
}

export interface SalesReport {
  status: string;
  order_count: number;
  total_amount: string;
}

export interface OccupancyReport {
  event_id: string;
  event_title: string;
  event_starts_at: string;
  total_quota: number;
  total_sold: number;
  occupancy_pct: string;
}

export interface TopClientReport {
  client_id: string;
  full_name: string | null;
  email: string;
  total_orders: number;
  total_spent: string;
}

export interface AuditStatsReport {
  action: string;
  actor_role: string | null;
  count: number;
}
