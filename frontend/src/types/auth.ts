export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MeResponse {
  id: string;
  email: string;
  user_type: string;
  role: string | null;
  full_name: string | null;
  discount_percent: number | null;
}
