"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, type ApiListJobsResponse, type ApiMeResponse } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const token = useMemo(() => getToken(), []);
  const [me, setMe] = useState<ApiMeResponse | null>(null);
  const [jobs, setJobs] = useState<ApiListJobsResponse["jobs"]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    (async () => {
      try {
        const meRes = await apiFetch<ApiMeResponse>("/v1/me", {}, token);
        setMe(meRes);
        const list = await apiFetch<ApiListJobsResponse>("/v1/jobs", {}, token);
        setJobs(list.jobs);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load dashboard");
      }
    })();
  }, [router, token]);

  return (
    <main className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-zinc-300">
            {me ? (
              <>
                Signed in as <span className="text-zinc-100">{me.email}</span> · Credits{" "}
                <span className="text-zinc-100">{me.credits_balance}</span>
              </>
            ) : (
              "Loading..."
            )}
          </p>
        </div>

        <div className="flex gap-3">
          <a className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200" href="/new">
            New job
          </a>
          <button
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-900"
            onClick={() => {
              clearToken();
              router.push("/");
            }}
          >
            Logout
          </button>
        </div>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40">
        <div className="border-b border-zinc-800 px-6 py-4">
          <h2 className="text-lg font-semibold">Recent jobs</h2>
        </div>
        <div className="divide-y divide-zinc-800">
          {jobs.length === 0 ? (
            <div className="px-6 py-8 text-sm text-zinc-400">No jobs yet. Create one.</div>
          ) : (
            jobs.map((j) => (
              <a key={j.job_id} className="block px-6 py-4 hover:bg-zinc-900" href={`/jobs/${j.job_id}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-zinc-100">Job {j.job_id.slice(0, 8)}</div>
                    <div className="mt-1 text-xs text-zinc-400">
                      {j.status} · res {j.resolution ?? "?"} · cost {j.cost_credits}
                    </div>
                  </div>
                  <div className="text-xs text-zinc-500">{new Date(j.updated_at).toLocaleString()}</div>
                </div>
              </a>
            ))
          )}
        </div>
      </section>
    </main>
  );
}


