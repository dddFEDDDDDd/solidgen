"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch, type ApiJobResponse } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function JobPage() {
  const router = useRouter();
  const params = useParams<{ jobId: string }>();
  const token = useMemo(() => getToken(), []);
  const [job, setJob] = useState<ApiJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const res = await apiFetch<ApiJobResponse>(`/v1/jobs/${params.jobId}`, {}, token);
        setJob(res);
        setError(null);
        if (res.status === "QUEUED" || res.status === "RUNNING") {
          timer = setTimeout(load, 2500);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load job");
      }
    }

    load();
    return () => timer && clearTimeout(timer);
  }, [params.jobId, router, token]);

  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Job</h1>
          <p className="mt-1 text-sm text-zinc-300">{params.jobId}</p>
        </div>
        <a className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-900" href="/dashboard">
          Back
        </a>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {!job ? (
          <p className="text-sm text-zinc-300">Loading...</p>
        ) : (
          <div className="space-y-3">
            <div className="text-sm">
              <span className="text-zinc-400">Status:</span> <span className="text-zinc-100">{job.status}</span>
            </div>
            <div className="text-sm">
              <span className="text-zinc-400">Cost:</span> <span className="text-zinc-100">{job.cost_credits}</span>
            </div>
            <div className="text-sm">
              <span className="text-zinc-400">Resolution:</span>{" "}
              <span className="text-zinc-100">{String(job.params?.resolution ?? "")}</span>
            </div>
            {job.error_text ? (
              <div className="rounded-lg border border-red-900/60 bg-red-950/30 p-3 text-sm text-red-200">
                {job.error_text}
              </div>
            ) : null}

            {job.status === "SUCCEEDED" && job.output_download_url ? (
              <div className="pt-3">
                <a
                  className="inline-flex rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200"
                  href={job.output_download_url}
                >
                  Download GLB
                </a>
                <p className="mt-2 text-xs text-zinc-400">Signed URL expires quickly; refresh if needed.</p>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </main>
  );
}




