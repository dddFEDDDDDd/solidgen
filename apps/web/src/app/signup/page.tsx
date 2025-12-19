"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, type ApiAuthResponse } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch<ApiAuthResponse>("/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md">
      <h1 className="text-2xl font-semibold">Create account</h1>
      <p className="mt-2 text-sm text-zinc-300">Start generating GLBs with TRELLIS.2.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <label className="block text-sm">
          <span className="text-zinc-300">Email</span>
          <input
            className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-zinc-300">Password</span>
          <input
            className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            minLength={8}
            required
          />
        </label>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        <button
          disabled={loading}
          className="w-full rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
          type="submit"
        >
          {loading ? "Creating..." : "Create account"}
        </button>
        <p className="text-center text-sm text-zinc-400">
          Already have an account?{" "}
          <a className="text-zinc-200 hover:text-white underline" href="/login">
            Login
          </a>
        </p>
      </form>
    </main>
  );
}




