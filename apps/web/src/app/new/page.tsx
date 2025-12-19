"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, API_BASE, type ApiCreateJobResponse, type ApiSignedUploadResponse } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function NewJobPage() {
  const router = useRouter();
  const token = useMemo(() => getToken(), []);
  const [file, setFile] = useState<File | null>(null);
  const [resolution, setResolution] = useState<512 | 1024 | 1536>(1024);
  const [seed, setSeed] = useState<number>(0);
  const [decimationTarget, setDecimationTarget] = useState<number>(500000);
  const [textureSize, setTextureSize] = useState<number>(2048);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!token) {
      router.push("/login");
      return;
    }
    if (!file) {
      setError("Please pick an image");
      return;
    }

    const ext = file.name.split(".").pop()?.toLowerCase() || "png";
    const fileExt = ext === "jpeg" ? "jpeg" : ext === "jpg" ? "jpg" : ext === "webp" ? "webp" : "png";
    const contentType =
      fileExt === "jpg" || fileExt === "jpeg"
        ? "image/jpeg"
        : fileExt === "webp"
          ? "image/webp"
          : "image/png";

    setStatus("Requesting upload URL...");
    const sign = await apiFetch<ApiSignedUploadResponse>(
      "/v1/uploads/sign",
      { method: "POST", body: JSON.stringify({ content_type: contentType, file_ext: fileExt }) },
      token,
    );

    setStatus("Uploading image to storage...");
    const putRes = await fetch(sign.upload_url, {
      method: "PUT",
      headers: { "Content-Type": contentType },
      body: file,
    });
    if (!putRes.ok) {
      throw new Error(`Upload failed: ${putRes.status} ${putRes.statusText}`);
    }

    setStatus("Creating job...");
    const job = await apiFetch<ApiCreateJobResponse>(
      "/v1/jobs",
      {
        method: "POST",
        body: JSON.stringify({
          input_gcs_uri: sign.gcs_uri,
          resolution,
          seed,
          decimation_target: decimationTarget,
          texture_size: textureSize,
        }),
      },
      token,
    );

    setStatus("Job queued. Redirecting...");
    router.push(`/jobs/${job.job_id}`);
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New job</h1>
        <p className="mt-1 text-sm text-zinc-300">
          Upload an image and generate a marketplace-ready GLB. API: <span className="text-zinc-100">{API_BASE}</span>
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <label className="block text-sm">
          <span className="text-zinc-300">Image</span>
          <input
            className="mt-2 block w-full text-sm"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm">
            <span className="text-zinc-300">Resolution</span>
            <select
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
              value={resolution}
              onChange={(e) => setResolution(parseInt(e.target.value, 10) as 512 | 1024 | 1536)}
            >
              <option value={512}>512</option>
              <option value={1024}>1024</option>
              <option value={1536}>1536</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-zinc-300">Seed</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
              type="number"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value || "0", 10))}
            />
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm">
            <span className="text-zinc-300">Decimation target</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
              type="number"
              value={decimationTarget}
              onChange={(e) => setDecimationTarget(parseInt(e.target.value || "0", 10))}
            />
          </label>
          <label className="block text-sm">
            <span className="text-zinc-300">Texture size</span>
            <select
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
              value={textureSize}
              onChange={(e) => setTextureSize(parseInt(e.target.value, 10))}
            >
              <option value={1024}>1024</option>
              <option value={2048}>2048</option>
              <option value={4096}>4096</option>
            </select>
          </label>
        </div>

        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        {status ? <p className="text-sm text-zinc-300">{status}</p> : null}

        <button className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200" type="submit">
          Generate
        </button>
      </form>
    </main>
  );
}


