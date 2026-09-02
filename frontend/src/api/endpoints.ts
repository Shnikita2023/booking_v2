import client from './client';
import type { LoginRequest, TokenResponse, MeResponse } from '../types/auth';
import type { PaginatedResponse } from '../types/common';
import type { EventRead, EventCreate, EventUpdate, EventMove, TicketTypeRead, TicketTypeCreate, TicketTypeUpdate } from '../types/event';
import type { ClientRead, ClientCreate, ClientUpdate } from '../types/client';
import type { UserRead, UserCreate, UserUpdate } from '../types/user';
import type { DiscountRead, DiscountCreate, DiscountUpdate } from '../types/discount';
import type { OrderRead, OrderCreateRequest } from '../types/order';
import type { PaymentRead } from '../types/payment';
import type { SettingRead, SettingSet } from '../types/settings';
import type { AuditRead } from '../types/audit';
import type { RevenueReport, RevenueByDateReport, SalesReport, OccupancyReport, TopClientReport, AuditStatsReport } from '../types/report';

// ── Auth ──
export const auth = {
  staffLogin: (data: LoginRequest) =>
    client.post<TokenResponse>('/staff/login', data),
  clientLogin: (data: LoginRequest) =>
    client.post<TokenResponse>('/auth/login', data),
  refresh: (refresh_token: string) =>
    client.post<TokenResponse>('/auth/refresh', { refresh_token }),
  me: () => client.get<MeResponse>('/auth/me'),
  logout: () => client.post('/auth/logout'),
};

// ── Events (admin) ──
export const events = {
  list: (limit = 20, offset = 0) =>
    client.get<PaginatedResponse<EventRead>>('/admin/events', { params: { limit, offset } }),
  get: (id: string) => client.get<EventRead>(`/admin/events/${id}`),
  create: (data: EventCreate) => client.post<EventRead>('/admin/events', data),
  update: (id: string, data: EventUpdate) => client.put<EventRead>(`/admin/events/${id}`, data),
  clone: (id: string) => client.post<EventRead>(`/admin/events/${id}/clone`),
  publish: (id: string) => client.post<EventRead>(`/admin/events/${id}/publish`),
  cancel: (id: string) => client.post<EventRead>(`/admin/events/${id}/cancel`),
  complete: (id: string) => client.post<EventRead>(`/admin/events/${id}/complete`),
  pauseSales: (id: string) => client.post<EventRead>(`/admin/events/${id}/pause-sales`),
  resumeSales: (id: string) => client.post<EventRead>(`/admin/events/${id}/resume-sales`),
  move: (id: string, data: EventMove) => client.post<EventRead>(`/admin/events/${id}/move`, data),
  listTicketTypes: (eventId: string) =>
    client.get<{ items: TicketTypeRead[] }>(`/admin/events/${eventId}/ticket-types`),
  createTicketType: (eventId: string, data: TicketTypeCreate) =>
    client.post<TicketTypeRead>(`/admin/events/${eventId}/ticket-types`, data),
  updateTicketType: (eventId: string, ttId: string, data: TicketTypeUpdate) =>
    client.put<TicketTypeRead>(`/admin/events/${eventId}/ticket-types/${ttId}`, data),
  deleteTicketType: (eventId: string, ttId: string) =>
    client.delete(`/admin/events/${eventId}/ticket-types/${ttId}`),
};

// ── Clients (admin) ──
export const clients = {
  list: (limit = 20, offset = 0) =>
    client.get<PaginatedResponse<ClientRead>>('/admin/clients', { params: { limit, offset } }),
  get: (id: string) => client.get<ClientRead>(`/admin/clients/${id}`),
  create: (data: ClientCreate) => client.post<ClientRead>('/admin/clients', data),
  update: (id: string, data: ClientUpdate) => client.put<ClientRead>(`/admin/clients/${id}`, data),
  block: (id: string) => client.post<ClientRead>(`/admin/clients/${id}/block`),
  unblock: (id: string) => client.post<ClientRead>(`/admin/clients/${id}/unblock`),
  delete: (id: string) => client.delete(`/admin/clients/${id}`),
  resetPassword: (id: string, password: string) =>
    client.post(`/admin/clients/${id}/reset-password`, { password }),
};

// ── Staff users (admin) ──
export const staffUsers = {
  list: (limit = 20, offset = 0) =>
    client.get<PaginatedResponse<UserRead>>('/admin/users', { params: { limit, offset } }),
  get: (id: string) => client.get<UserRead>(`/admin/users/${id}`),
  create: (data: UserCreate) => client.post<UserRead>('/admin/users', data),
  update: (id: string, data: UserUpdate) => client.put<UserRead>(`/admin/users/${id}`, data),
  block: (id: string) => client.post<UserRead>(`/admin/users/${id}/block`),
  unblock: (id: string) => client.post<UserRead>(`/admin/users/${id}/unblock`),
  delete: (id: string) => client.delete(`/admin/users/${id}`),
  resetPassword: (id: string, password: string) =>
    client.post(`/admin/users/${id}/reset-password`, { password }),
};

// ── Discounts (admin) ──
export const discounts = {
  list: (limit = 20, offset = 0) =>
    client.get<PaginatedResponse<DiscountRead>>('/admin/discounts', { params: { limit, offset } }),
  get: (id: string) => client.get<DiscountRead>(`/admin/discounts/${id}`),
  create: (data: DiscountCreate) => client.post<DiscountRead>('/admin/discounts', data),
  update: (id: string, data: DiscountUpdate) => client.put<DiscountRead>(`/admin/discounts/${id}`, data),
  delete: (id: string) => client.delete(`/admin/discounts/${id}`),
};

// ── Cashier / Staff orders ──
export const cashier = {
  sell: (data: OrderCreateRequest) => client.post<OrderRead>('/staff/orders', data),
  refund: (orderId: string) => client.post<PaymentRead>(`/staff/orders/${orderId}/refund`),
  cancel: (orderId: string) => client.post<OrderRead>(`/staff/orders/${orderId}/cancel`),
  list: (limit = 20, offset = 0) =>
    client.get<PaginatedResponse<OrderRead>>('/staff/orders', { params: { limit, offset } }),
};

// ── Reports ──
export const reports = {
  revenue: (fromDate?: string, toDate?: string) =>
    client.get<RevenueReport[]>('/staff/reports/revenue', { params: { from_date: fromDate, to_date: toDate } }),
  revenueByDate: (fromDate?: string, toDate?: string) =>
    client.get<RevenueByDateReport[]>('/staff/reports/revenue-by-date', { params: { from_date: fromDate, to_date: toDate } }),
  sales: (fromDate?: string, toDate?: string) =>
    client.get<SalesReport[]>('/staff/reports/sales', { params: { from_date: fromDate, to_date: toDate } }),
  occupancy: () =>
    client.get<OccupancyReport[]>('/staff/reports/occupancy'),
  topClients: (limit = 10, offset = 0) =>
    client.get<TopClientReport[]>('/staff/reports/top-clients', { params: { limit, offset } }),
  auditStats: (fromDate?: string, toDate?: string) =>
    client.get<AuditStatsReport[]>('/staff/reports/audit-stats', { params: { from_date: fromDate, to_date: toDate } }),
};

// ── Audit (admin) ──
export const audit = {
  list: (params: Record<string, string | number | undefined>) =>
    client.get<PaginatedResponse<AuditRead>>('/admin/audit', { params }),
};

// ── Settings (admin) ──
export const settings = {
  list: () => client.get<SettingRead[]>('/admin/settings'),
  get: (key: string) => client.get<SettingRead>(`/admin/settings/${key}`),
  set: (key: string, data: SettingSet) => client.put<SettingRead>(`/admin/settings/${key}`, data),
};
