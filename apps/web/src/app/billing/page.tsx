"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, type ApiMeResponse, type ApiNowPaymentsInvoiceResponse, type ApiStripeCheckoutResponse } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function BillingPage() {
  const router = useRouter();
  const token = useMemo(() => getToken(), []);
  const [me, setMe] = useState<ApiMeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [credits, setCredits] = useState(10);
  const [payCurrency, setPayCurrency] = useState("usdt");

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    (async () => {
      try {
        const meRes = await apiFetch<ApiMeResponse>("/v1/me", {}, token);
        setMe(meRes);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
  }, [router, token]);

  async function buyStripe() {
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch<ApiStripeCheckoutResponse>(
        "/v1/billing/stripe/checkout-session",
        { method: "POST", body: JSON.stringify({ credits }) },
        token,
      );
      window.location.href = res.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Stripe checkout failed");
      setLoading(false);
    }
  }

  async function buyCrypto() {
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch<ApiNowPaymentsInvoiceResponse>(
        "/v1/billing/nowpayments/invoice",
        { method: "POST", body: JSON.stringify({ credits, pay_currency: payCurrency }) },
        token,
      );
      window.location.href = res.invoice_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "NOWPayments invoice failed");
      setLoading(false);
    }
  }

  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Billing</h1>
        <p className="mt-1 text-sm text-zinc-300">
          {me ? (
            <>
              Credits balance: <span className="text-zinc-100">{me.credits_balance}</span>
            </>
          ) : (
            "Loading..."
          )}
        </p>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="block text-sm md:col-span-1">
            <span className="text-zinc-300">Credits</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2"
              type="number"
              min={1}
              value={credits}
              onChange={(e) => setCredits(parseInt(e.target.value || "1", 10))}
            />
          </label>

          <div className="md:col-span-2 grid gap-3 md:grid-cols-2">
            <button
              disabled={loading}
              className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
              onClick={buyStripe}
            >
              Buy with Stripe (card)
            </button>

            <div className="flex gap-2">
              <select
                className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
                value={payCurrency}
                onChange={(e) => setPayCurrency(e.target.value)}
              >
                <option value="usdt">USDT</option>
                <option value="btc">BTC</option>
                <option value="eth">ETH</option>
              </select>
              <button
                disabled={loading}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-900 disabled:opacity-50"
                onClick={buyCrypto}
              >
                Crypto
              </button>
            </div>
          </div>
        </div>

        <p className="mt-4 text-xs text-zinc-500">
          v1 pricing placeholder: <span className="text-zinc-200">$1 = 1 credit</span>. Adjust later.
        </p>
      </section>
    </main>
  );
}




