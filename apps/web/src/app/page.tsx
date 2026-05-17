const boundaries = ["No AI", "No database", "No auth", "No uploads", "No video"];

export default function Home() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-10 lg:px-16">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col justify-between gap-12">
        <header className="flex items-center justify-between gap-4">
          <p className="text-sm font-semibold tracking-[0.2em] text-emerald-800 uppercase">
            FitPlate Coach
          </p>
          <p className="rounded-full border border-stone-300 px-3 py-1 text-sm text-stone-700">
            Scaffold v0
          </p>
        </header>

        <div className="grid items-center gap-10 lg:grid-cols-[1fr_22rem]">
          <div className="space-y-7">
            <div className="space-y-4">
              <p className="text-sm font-medium text-emerald-800">
                Minimal monorepo milestone
              </p>
              <h1 className="max-w-3xl text-4xl font-semibold text-stone-950 sm:text-5xl">
                Production-shaped foundations for food and form coaching.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-stone-700">
                This first screen is intentionally static. The next milestones
                will add food photo mock analysis, correction loops, and safe
                uncertainty-first product behavior.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {boundaries.map((boundary) => (
                <span
                  key={boundary}
                  className="rounded-full border border-stone-300 bg-white/70 px-3 py-1 text-sm font-medium text-stone-700"
                >
                  {boundary}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-stone-300 bg-white p-6 shadow-sm">
            <div className="mx-auto flex aspect-square max-w-64 items-center justify-center rounded-full bg-stone-100">
              <div className="grid h-40 w-40 grid-cols-2 gap-3 rounded-full border-8 border-white bg-white p-4 shadow-inner">
                <div className="rounded-tl-full bg-emerald-600" />
                <div className="rounded-tr-full bg-amber-400" />
                <div className="rounded-bl-full bg-rose-500" />
                <div className="rounded-br-full bg-sky-500" />
              </div>
            </div>
            <div className="mt-6 space-y-2 text-center">
              <h2 className="text-lg font-semibold text-stone-950">
                Static home page only
              </h2>
              <p className="text-sm leading-6 text-stone-600">
                The frontend does not call the API in this milestone.
              </p>
            </div>
          </div>
        </div>

        <footer className="text-sm text-stone-600">
          Health endpoint available at <code>/api/v0/health</code>.
        </footer>
      </section>
    </main>
  );
}
