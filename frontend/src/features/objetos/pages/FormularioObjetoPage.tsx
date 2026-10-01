import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2 } from "lucide-react";
import { cn } from "cn";
import { ApiError } from "@/core/api/client";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Campo, claseSelect } from "@/shared/components/Campo";
import { ChipsSugerencia } from "@/shared/components/ChipsSugerencia";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { TiraSegmento } from "@/shared/components/TiraLed";
import { ajustarAExistente } from "@/shared/lib/ubicacion";
import { useCategorias, type Categoria } from "@/features/categorias/api";
import { IdentificarConFoto } from "@/features/identificacion/IdentificarConFoto";
import { VISION_ACTIVA } from "@/features/identificacion/api";
import { useAlmacenes, usePlano } from "@/features/plano/api";
import { SelectorLed, type PosicionOcupada } from "../components/SelectorLed";
import { useActualizarObjeto, useCrearObjeto, useObjeto } from "../api";
import { REGEX_COLOR, objetoSchema, type ObjetoFormulario } from "../schema";
import type { CuerpoObjeto, Objeto } from "../tipos";

const COLORES = ["#00FF00", "#00AAFF", "#FFD400", "#FF8800", "#FF3B30", "#AF52DE", "#FFFFFF"];

function Seccion({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 rounded-xl border bg-card p-5 shadow-xs">
      <div className="space-y-1">
        <h2 className="font-semibold">{titulo}</h2>
        {descripcion && <p className="text-sm text-muted-foreground">{descripcion}</p>}
      </div>
      {children}
    </section>
  );
}

export default function FormularioObjetoPage() {
  const { id } = useParams();
  const edicion = id !== undefined;
  const consulta = useObjeto(id ?? "", edicion);
  const categorias = useCategorias();

  // El formulario se monta con los datos ya cargados: así los valores iniciales
  // (y la categoría del <select>) llegan completos desde el primer render.
  if (categorias.isPending || (edicion && consulta.isPending)) {
    return (
      <div className="mx-auto grid w-full max-w-3xl gap-6" aria-busy="true">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (categorias.isError || (edicion && consulta.isError)) {
    return (
      <EmptyState
        icono={AlertCircle}
        titulo="No se pudo abrir el formulario"
        descripcion={(consulta.error ?? categorias.error)?.message ?? "Inténtalo de nuevo."}
        accion={
          <Link to="/objetos" className={buttonVariants({ variant: "outline" })}>
            Volver a objetos
          </Link>
        }
      />
    );
  }

  return <Formulario key={consulta.data?.object_id ?? "nuevo"} objeto={edicion ? consulta.data : undefined} categorias={categorias.data} />;
}

function Formulario({ objeto, categorias }: { objeto?: Objeto; categorias: Categoria[] }) {
  const edicion = objeto !== undefined;
  const navigate = useNavigate();
  const crear = useCrearObjeto();
  const actualizar = useActualizarObjeto(objeto?.object_id ?? "");

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    control,
    formState: { errors },
  } = useForm<ObjetoFormulario>({
    resolver: zodResolver(objetoSchema),
    mode: "onTouched",
    defaultValues: objeto ? { ...objeto, object_id: "" } : { object_id: "", categoria: "", color_indicador: "#00FF00" },
  });

  const [posicion, color, almacenElegido, pasilloElegido, anaquelElegido, nivelElegido] = useWatch({
    control,
    name: ["posicion_led", "color_indicador", "almacen_id", "pasillo", "anaquel", "nivel"],
  });

  const almacenes = useAlmacenes();
  const plano = usePlano(almacenElegido?.trim() || undefined);
  const pasillos = plano.data?.pasillos ?? [];
  const anaqueles = pasillos.find((p) => p.pasillo === pasilloElegido?.trim())?.anaqueles ?? [];
  const niveles = anaqueles.find((a) => a.anaquel === anaquelElegido?.trim())?.niveles ?? [];

  const almacenesConocidos = almacenes.data?.map((a) => a.almacen_id) ?? [];
  const opcionesPasillo = pasillos.map((p) => p.pasillo);
  const opcionesAnaquel = anaqueles.map((a) => a.anaquel);
  const opcionesNivel = niveles.map((n) => n.nivel);

  // Las posiciones que ya usa otro objeto de este almacen.
  const ocupadas = new Map<number, PosicionOcupada>();
  for (const p of pasillos)
    for (const a of p.anaqueles)
      for (const n of a.niveles)
        for (const o of n.objetos)
          if (o.object_id !== objeto?.object_id)
            ocupadas.set(o.posicion_led, { nombre: o.nombre, color_indicador: o.color_indicador });

  const escribir = (campo: "almacen_id" | "pasillo" | "anaquel" | "nivel", valor: string) =>
    setValue(campo, valor, { shouldValidate: true, shouldDirty: true });
  const colorVista = REGEX_COLOR.test(color ?? "") ? color : "#00FF00";
  const posicionVista = Number.isInteger(posicion) && posicion >= 0 ? posicion : null;
  const enviando = crear.isPending || actualizar.isPending;

  const elegirColor = (valor: string) =>
    setValue("color_indicador", valor.toUpperCase(), { shouldValidate: true, shouldDirty: true });

  const guardar = (datos: ObjetoFormulario) => {
    const cuerpo: CuerpoObjeto = {
      nombre: datos.nombre,
      categoria: datos.categoria,
      almacen_id: datos.almacen_id,
      pasillo: datos.pasillo,
      anaquel: datos.anaquel,
      nivel: datos.nivel,
      posicion_led: datos.posicion_led,
      color_indicador: datos.color_indicador.toUpperCase(),
    };
    const alTerminar = (o: Objeto) => navigate(`/objetos/${encodeURIComponent(o.object_id)}`);

    const alFallar = (e: unknown) => {
      if (!(e instanceof ApiError) || e.status !== 409) return;
      const campo = (e.details as { campo?: string } | undefined)?.campo;
      if (campo === "posicion_led") setError("posicion_led", { message: e.message });
      else setError("object_id", { message: "Ese código ya está en uso." });
    };

    if (edicion) {
      actualizar.mutate(cuerpo, { onSuccess: alTerminar, onError: alFallar });
      return;
    }
    crear.mutate(datos.object_id ? { ...cuerpo, object_id: datos.object_id } : cuerpo, {
      onSuccess: alTerminar,
      onError: alFallar,
    });
  };

  return (
    <form onSubmit={handleSubmit(guardar)} noValidate className="mx-auto grid w-full max-w-3xl gap-6">
      <PageHeader
        titulo={edicion ? "Editar ubicación" : "Registrar objeto"}
        descripcion={
          edicion
            ? `Actualiza dónde está “${objeto.nombre}” y qué LED lo señala.`
            : "Da de alta un objeto y el LED que lo señala en su anaquel."
        }
      />

      {!edicion && VISION_ACTIVA && (
        <IdentificarConFoto
          categorias={categorias}
          alUsar={({ nombre, categoria }) => {
            const opciones = { shouldValidate: true, shouldDirty: true };
            if (nombre) setValue("nombre", nombre, opciones);
            if (categoria) setValue("categoria", categoria, opciones);
          }}
        />
      )}

      <Seccion titulo="Datos del objeto">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="nombre" etiqueta="Nombre" error={errors.nombre?.message} className="sm:col-span-2">
            <Input id="nombre" autoComplete="off" aria-invalid={!!errors.nombre} {...register("nombre")} />
          </Campo>
          <Campo id="categoria" etiqueta="Categoría" error={errors.categoria?.message}>
            <select id="categoria" aria-invalid={!!errors.categoria} className={claseSelect} {...register("categoria")}>
              <option value="">Elige una categoría</option>
              {categorias.map((c) => (
                <option key={c.categoria_id} value={c.categoria_id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Campo>
          {!edicion && (
            <Campo
              id="object_id"
              etiqueta="Código (opcional)"
              error={errors.object_id?.message}
              ayuda="Si lo dejas vacío se genera uno automáticamente."
            >
              <Input
                id="object_id"
                autoComplete="off"
                placeholder="obj-000123"
                aria-invalid={!!errors.object_id}
                {...register("object_id")}
              />
            </Campo>
          )}
        </div>
      </Seccion>

      <Seccion
        titulo="Ubicación en el almacén"
        descripcion="Toca lo que ya existe o escribe un sitio nuevo, tal como está rotulado físicamente."
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <Campo id="almacen_id" etiqueta="Almacén" error={errors.almacen_id?.message}>
            <Input
              id="almacen_id"
              placeholder="almacen-01"
              autoComplete="off"
              aria-invalid={!!errors.almacen_id}
              {...register("almacen_id", {
                onBlur: (e) =>
                  escribir("almacen_id", ajustarAExistente(e.target.value, almacenesConocidos)),
              })}
            />
            <ChipsSugerencia
              etiqueta="Almacenes que ya existen"
              opciones={almacenesConocidos}
              valor={almacenElegido}
              onElegir={(v) => escribir("almacen_id", v)}
            />
          </Campo>
          <Campo id="pasillo" etiqueta="Pasillo" error={errors.pasillo?.message}>
            <Input
              id="pasillo"
              autoComplete="off"
              aria-invalid={!!errors.pasillo}
              {...register("pasillo", {
                onBlur: (e) => escribir("pasillo", ajustarAExistente(e.target.value, opcionesPasillo)),
              })}
            />
            <ChipsSugerencia
              etiqueta="Pasillos de este almacén"
              opciones={opcionesPasillo}
              valor={pasilloElegido}
              onElegir={(v) => escribir("pasillo", v)}
            />
          </Campo>
          <Campo id="anaquel" etiqueta="Anaquel" error={errors.anaquel?.message}>
            <Input
              id="anaquel"
              autoComplete="off"
              aria-invalid={!!errors.anaquel}
              {...register("anaquel", {
                onBlur: (e) => escribir("anaquel", ajustarAExistente(e.target.value, opcionesAnaquel)),
              })}
            />
            <ChipsSugerencia
              etiqueta="Anaqueles de este pasillo"
              opciones={opcionesAnaquel}
              valor={anaquelElegido}
              onElegir={(v) => escribir("anaquel", v)}
            />
          </Campo>
          <Campo id="nivel" etiqueta="Nivel" error={errors.nivel?.message}>
            <Input
              id="nivel"
              autoComplete="off"
              aria-invalid={!!errors.nivel}
              {...register("nivel", {
                onBlur: (e) => escribir("nivel", ajustarAExistente(e.target.value, opcionesNivel)),
              })}
            />
            <ChipsSugerencia
              etiqueta="Niveles de este anaquel"
              opciones={opcionesNivel}
              valor={nivelElegido}
              onElegir={(v) => escribir("nivel", v)}
            />
          </Campo>
        </div>
      </Seccion>

      <Seccion
        titulo="Indicador LED"
        descripcion="Posición del LED en la tira del almacén y color con el que se encenderá."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo
            id="posicion_led"
            etiqueta="Posición en la tira"
            error={errors.posicion_led?.message}
            ayuda="También puedes escribir el número si tu tira es más larga."
          >
            <Input
              id="posicion_led"
              type="number"
              inputMode="numeric"
              min={0}
              max={65535}
              className="sm:max-w-32"
              aria-invalid={!!errors.posicion_led}
              {...register("posicion_led", { valueAsNumber: true })}
            />
          </Campo>
          <Campo id="color_indicador" etiqueta="Color" error={errors.color_indicador?.message}>
            <div className="flex items-center gap-2">
              <input
                type="color"
                aria-label="Elegir color personalizado"
                value={colorVista.toLowerCase()}
                onChange={(e) => elegirColor(e.target.value)}
                className="size-11 shrink-0 cursor-pointer rounded-lg border bg-transparent p-1 md:size-9"
              />
              <Input
                id="color_indicador"
                className="font-mono uppercase"
                aria-invalid={!!errors.color_indicador}
                {...register("color_indicador")}
              />
            </div>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Colores sugeridos">
              {COLORES.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-label={`Color ${c}`}
                  aria-pressed={colorVista.toUpperCase() === c}
                  onClick={() => elegirColor(c)}
                  className={cn(
                    "size-9 rounded-full border-2 transition-transform hover:scale-110 md:size-7",
                    colorVista.toUpperCase() === c ? "border-foreground" : "border-transparent ring-1 ring-border",
                  )}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </Campo>
        </div>

        <div className="grid gap-2">
          <p className="text-xs font-medium text-muted-foreground">Elige la posición tocándola en la tira</p>
          <SelectorLed
            valor={posicionVista}
            color={colorVista}
            ocupadas={ocupadas}
            onElegir={(n) => setValue("posicion_led", n, { shouldValidate: true, shouldDirty: true })}
          />
        </div>

        <div className="grid gap-2">
          <p className="text-xs font-medium text-muted-foreground">Así se verá en el anaquel</p>
          <TiraSegmento centro={posicionVista ?? 0} color={colorVista} encendido={posicionVista !== null} />
        </div>
      </Seccion>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
          Cancelar
        </Button>
        <Button type="submit" disabled={enviando}>
          {enviando && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {edicion ? "Guardar cambios" : "Registrar objeto"}
        </Button>
      </div>
    </form>
  );
}
