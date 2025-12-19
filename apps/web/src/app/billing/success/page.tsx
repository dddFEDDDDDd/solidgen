export default function BillingSuccessPage() {
  return (
    <main className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Payment received</h1>
      <p className="text-sm text-zinc-300">
        Thanks! Your credits will be added after the payment webhook is processed. If you don’t see an updated balance
        yet, wait a few seconds and refresh.
      </p>
      <a className="inline-flex rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200" href="/dashboard">
        Back to dashboard
      </a>
    </main>
  );
}




