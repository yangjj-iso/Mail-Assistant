const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function fetchWithTimeout(url: string, ms = 3000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return fetch(url, { signal: controller.signal }).finally(() => clearTimeout(timer));
}

export interface Account {
  ID: number;
  email: string;
  imap_host: string;
  imap_port: number;
  status: string;
  CreatedAt: string;
}

export interface Email {
  ID: number;
  account_id: number;
  message_id: string;
  subject: string;
  from_addr: string;
  date: string;
  body_preview: string;
  stage1_label: string;
  stage2_label: string | null;
  final_label: string;
  classified_at: string;
}

export interface EmailListResponse {
  items: Email[];
  total: number;
  page: number;
  size: number;
}

export interface LabelStat {
  label: string;
  count: number;
}

export async function fetchAccounts(): Promise<Account[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/accounts`);
  return res.json();
}

export async function createAccount(data: {
  email: string;
  password: string;
  imap_host: string;
  imap_port: number;
}): Promise<Account> {
  const res = await fetch(`${API_BASE}/api/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Failed to create account");
  }
  return res.json();
}

export async function deleteAccount(id: number): Promise<void> {
  await fetch(`${API_BASE}/api/accounts/${id}`, { method: "DELETE" });
}

export async function fetchEmails(params: {
  page?: number;
  size?: number;
  label?: string;
}): Promise<EmailListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.size) query.set("size", String(params.size));
  if (params.label) query.set("label", params.label);
  const res = await fetchWithTimeout(`${API_BASE}/api/emails?${query}`);
  return res.json();
}

export async function fetchEmail(id: number): Promise<Email> {
  const res = await fetchWithTimeout(`${API_BASE}/api/emails/${id}`);
  return res.json();
}

export async function fetchStats(): Promise<LabelStat[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/stats`);
  return res.json();
}

export interface Application {
  id: number;
  account_id: number;
  company: string;
  position: string;
  stage: string;
  last_email_id: number;
  next_time: string | null;
  next_round: string;
  location: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationsResponse {
  items: Application[];
  grouped: Record<string, Application[]>;
}

export async function fetchApplications(): Promise<ApplicationsResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/applications`);
  return res.json();
}

export async function updateApplication(
  id: number,
  data: { stage?: string; notes?: string; next_time?: string }
): Promise<Application> {
  const res = await fetch(`${API_BASE}/api/applications/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function deleteApplication(id: number): Promise<void> {
  await fetch(`${API_BASE}/api/applications/${id}`, { method: "DELETE" });
}

export async function fetchUpcoming(): Promise<Application[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/applications/upcoming`);
  return res.json();
}
