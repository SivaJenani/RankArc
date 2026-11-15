import client from './client';
import type { User } from '../types';

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const register = async (
  email: string,
  password: string,
  name: string
): Promise<AuthResponse> => {
  const { data } = await client.post<AuthResponse>('/api/auth/register', {
    email,
    password,
    name,
  });
  return data;
};

/** Login sends application/x-www-form-urlencoded (OAuth2PasswordRequestForm) */
export const login = async (
  email: string,
  password: string
): Promise<AuthResponse> => {
  const form = new URLSearchParams();
  form.append('username', email);  // OAuth2 uses "username"
  form.append('password', password);
  const { data } = await client.post<AuthResponse>('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
};

export const getMe = async (): Promise<User> => {
  const { data } = await client.get<User>('/api/auth/me');
  return data;
};
