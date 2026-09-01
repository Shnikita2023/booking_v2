export interface ClientRead {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  is_active: boolean;
  discount_percent: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ClientCreate {
  email: string;
  full_name?: string | null;
  phone?: string | null;
  password: string;
  discount_percent?: number;
}

export type ClientUpdate = Partial<Omit<ClientCreate, 'password'>>;
