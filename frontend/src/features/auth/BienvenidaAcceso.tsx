/** Presentación de la app: qué es Mamagui y qué hace cada rol. */
export function BienvenidaAcceso() {
  return (
    <section className="flex flex-col justify-center gap-8">
      <div>
        <h1 className="text-4xl leading-tight font-bold tracking-tight md:text-5xl">
          Bienvenido a Mamagui, <span className="text-primary">sin buscar a ciegas.</span>
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-relaxed text-muted-foreground">
          En Mamagui Ferretería sabemos dónde está cada herramienta, tornillo y refacción: su pasillo, anaquel y
          nivel. Elige cómo vas a usarlo.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border p-6">
          <p className="text-xs font-bold tracking-wider text-primary">OPERADOR</p>
          <h2 className="mt-2 text-lg font-semibold">Buscar y registrar</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Localiza objetos, registra entradas y salidas y da de alta material con foto.
          </p>
        </article>
        <article className="rounded-2xl border p-6">
          <p className="text-xs font-bold tracking-wider text-primary">ADMINISTRADOR</p>
          <h2 className="mt-2 text-lg font-semibold">Gestionar el catálogo</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Crea categorías, revisa el plano y consulta las métricas de tiempo de búsqueda.
          </p>
        </article>
      </div>
    </section>
  );
}
