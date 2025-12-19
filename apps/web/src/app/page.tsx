export default function HomePage() {
  return (
    <main className="space-y-10">
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-8">
        <h1 className="text-3xl font-semibold tracking-tight">Image → 3D assets, production-focused.</h1>
        <p className="mt-3 max-w-2xl text-zinc-300">
          Solidgen wraps Microsoft TRELLIS.2 into a platform with job queues, GPU workers, post-processing, and
          marketplace-ready GLB exports.
        </p>
        <div className="mt-6 flex gap-3">
          <a
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-zinc-200"
            href="/signup"
          >
            Create account
          </a>
          <a className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-900" href="/login">
            Sign in
          </a>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <h2 className="text-lg font-semibold">Async GPU jobs</h2>
          <p className="mt-2 text-sm text-zinc-300">Queue jobs via Pub/Sub and run inference on a dedicated GPU VM.</p>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <h2 className="text-lg font-semibold">GLB post-processing</h2>
          <p className="mt-2 text-sm text-zinc-300">Exports are baked/UV’d via O-Voxel’s `to_glb` pipeline.</p>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <h2 className="text-lg font-semibold">Credits + payments</h2>
          <p className="mt-2 text-sm text-zinc-300">Stripe + NOWPayments webhook-driven credits ledger.</p>
        </div>
      </section>
    </main>
  );
}


