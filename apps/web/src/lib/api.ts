export type ApiAuthResponse = { access_token: string; token_type: string };

export type ApiMeResponse = { user_id: string; email: string; credits_balance: number };

export type ApiSignedUploadResponse = {
  upload_url: string;
  gcs_uri: string;
  object_name: string;
  expires_in_minutes: number;
};

export type ApiCreateJobResponse = { job_id: string; status: string; cost_credits: number };

export type ApiJobResponse = {
  job_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  input_gcs_uri: string;
  output_gcs_uri?: string | null;
  output_download_url?: string | null;
  error_text?: string | null;
  cost_credits: number;
  params: Record<string, unknown>;
};

export type ApiListJobsResponse = {
  jobs: Array<{ job_id: string; status: string; created_at: string; updated_at: string; resolution?: number | null; cost_credits: number }>;
};

export type ApiStripeCheckoutResponse = { url: string };
export type ApiNowPaymentsInvoiceResponse = { invoice_url: string; invoice_id: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

export async function apiFetch<T>(path: string, opts: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(opts.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${msg}`);
  }
  return (await res.json()) as T;
}

export { API_BASE };


