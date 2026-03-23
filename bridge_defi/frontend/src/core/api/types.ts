export interface ApiError {
  ok: false;
  code: string;
  message: string;
}

export type ApiResponse<T> =
  | { ok: true; data: T; error: null }
  | { ok: false; data: null; error: ApiError };

export function ok<T>(data: T): ApiResponse<T> {
  return { ok: true, data, error: null };
}

export function err(code: string, message: string): ApiResponse<never> {
  return { ok: false, data: null, error: { ok: false, code, message } };
}
