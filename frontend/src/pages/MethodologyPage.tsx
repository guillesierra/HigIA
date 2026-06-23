export function MethodologyPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Methods and limits</p>
          <h1>Metodologia</h1>
          <p>HigIA separa fuentes, descarga, normalizacion, almacenamiento y visualizacion para revisar cada dato contra su procedencia publica.</p>
        </div>
      </header>

      <section className="method-grid">
        <article className="panel">
          <h2>ATC</h2>
          <p>La clasificacion ATC agrupa medicamentos por sistema, propiedades terapeuticas, farmacologicas y quimicas.</p>
        </article>
        <article className="panel">
          <h2>DDD</h2>
          <p>DDD es una unidad tecnica de comparacion de consumo y no equivale necesariamente a una dosis prescrita individual.</p>
        </article>
        <article className="panel">
          <h2>DHD</h2>
          <p>DHD expresa dosis diarias definidas por mil habitantes y dia, util para comparar periodos o territorios cuando la metodologia es compatible.</p>
        </article>
        <article className="panel">
          <h2>Fuentes</h2>
          <p>La web lee JSON estaticos exportados desde fuentes publicas y mantiene URL, fecha de acceso, raw file y version de parser cuando existen.</p>
        </article>
        <article className="panel">
          <h2>Limitaciones</h2>
          <p>Los PDFs pueden requerir revision manual. Si una fuente no publica datos estructurados, HigIA cataloga el documento y no inventa metricas.</p>
        </article>
        <article className="panel">
          <h2>Notas legales</h2>
          <p>No hay login ni datos personales. La redistribucion de datasets depende de la licencia y terminos de cada fuente original.</p>
        </article>
      </section>
    </div>
  );
}

