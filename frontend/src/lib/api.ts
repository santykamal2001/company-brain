const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────
export interface Me {
  id: string;
  email: string;
  username: string;
  role: string;
  department: string | null;
}

export const login = (email: string, password: string) =>
  request<{ access_token: string }>("POST", "/api/auth/login", { email, password });

export const logout = () => request<void>("POST", "/api/auth/logout");

export const getMe = () => request<Me>("GET", "/api/auth/me");

// ─── Query ─────────────────────────────────────────────────────────────────
export interface Source {
  document_title: string;
  chunk_id: string;
  score: number;
  excerpt: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  chunks_used: number;
  latency_ms: number;
  retrieval_mode: string;
  graph_entities_used: string[];
  decision_trail_used: boolean;
  denied_chunk_count: number;
}

export const query = (question: string, n_results = 8) =>
  request<QueryResponse>("POST", "/api/query/", { question, n_results });

// ─── Documents ─────────────────────────────────────────────────────────────
export interface Document {
  id: string;
  title: string;
  source_type: string;
  status: string;
  chunk_count: number;
  classification: string;
  allowed_departments: string[];
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
}

export const listDocuments = () => request<Document[]>("GET", "/api/documents/");

export const uploadDocument = async (
  file: File,
  classification = "internal",
  allowed_departments = "",
): Promise<{ document_id: string; status: string }> => {
  const form = new FormData();
  form.append("file", file);
  form.append("classification", classification);
  form.append("allowed_departments", allowed_departments);
  const res = await fetch(`${BASE}/api/documents/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
};

export const reindexDocument = (id: string) =>
  request<void>("POST", `/api/documents/${id}/reindex`);

export const deleteDocument = (id: string) =>
  request<void>("DELETE", `/api/documents/${id}`);

// ─── Users ─────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
}

export const listUsers = () => request<User[]>("GET", "/api/users/");

export const createUser = (body: {
  email: string;
  username: string;
  password?: string;
  role: string;
  department_id?: string;
}) => request<User>("POST", "/api/users/", body);

export const updateUser = (id: string, body: Partial<User>) =>
  request<User>("PATCH", `/api/users/${id}`, body);

// ─── Analytics ─────────────────────────────────────────────────────────────
export interface AnalyticsOverview {
  document_count: number;
  total_queries: number;
  access_denials: number;
}

export const getOverview = () => request<AnalyticsOverview>("GET", "/api/analytics/overview");

export const getQueryHistory = () =>
  request<{ question: string; retrieval_mode: string; latency_ms: number; timestamp: string }[]>(
    "GET",
    "/api/analytics/query-history",
  );

export const getHealthEvents = () =>
  request<{ id: string; event_type: string; severity: string; title: string; description: string }[]>(
    "GET",
    "/api/analytics/health-events",
  );
