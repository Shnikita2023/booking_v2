export interface SettingRead {
  key: string;
  value: unknown;
  description: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SettingSet {
  value: unknown;
  description?: string | null;
}
