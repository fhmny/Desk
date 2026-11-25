export type Role = 'admin' | 'teacher' | 'designer';
export type Kind = 'image' | 'video';
export type RequestStatus = 'submitted' | 'accepted' | 'in_progress' | 'revision_requested' | 'completed' | 'canceled';
export interface Quota { total: number; reserved: number; completed: number; available: number }
export interface User { id: number; name: string; email: string; role: Role; active: boolean; subject: string | null; facebook: string | null; tiktok: string | null; youtube: string | null; designer_id: number | null; image_limit: number; video_limit: number; quotas?: { image: Quota; video: Quota } }
export interface DeskRequest { id: number; teacher_id: number; designer_id: number; kind: Kind; title: string; brief: string; status: RequestStatus; created_at: string; updated_at: string }
export interface DeskMessage { id: number; author_id: number; body: string; created_at: string }
export interface DeskLink { id: number; author_id: number; url: string; label: string; kind: 'reference' | 'draft' | 'final'; created_at: string }
export interface DeskDetail extends DeskRequest { teacher_profile: Pick<User, 'name' | 'subject' | 'facebook' | 'tiktok' | 'youtube'> | null; messages: DeskMessage[]; links: DeskLink[] }

const root = (import.meta.env.VITE_API_URL || '') + '/api/v1/desk';

export function getToken() { return localStorage.getItem('desk_token'); }
export function setToken(token: string) { localStorage.setItem('desk_token', token); }
export function clearToken() { localStorage.removeItem('desk_token'); }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(root + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/login') clearToken();
    throw new Error(typeof body.detail === 'string' ? body.detail : 'تعذر تنفيذ الطلب. راجع البيانات وحاول مرة أخرى.');
  }
  return body as T;
}

export const post = <T,>(path: string, body?: unknown) => api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
