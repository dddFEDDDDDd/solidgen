export default function BillingCancelPage() {
  return (
    <main className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Payment cancelled</h1>
      <p className="text-sm text-zinc-300">No worries — you can try again any time.</p>
      <a className="inline-flex rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-900" href="/billing">
        Back to billing
      </a>
    </main>
  );
}




