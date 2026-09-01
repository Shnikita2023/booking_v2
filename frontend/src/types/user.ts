export type RoleCode = 'admin' | 'manager' | 'cashier';

export interface UserRead {
  id: string;
  email: string;
  full_name: string | null;
  role_code: RoleCode;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface UserCreate {
  email: string;
  password: string;
  role_code: RoleCode;
}

export interface UserUpdate {
  full_name?: string | null;
  role_code?: RoleCode;
  is_active?: boolean;
}
