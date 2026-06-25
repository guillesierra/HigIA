const ATC_NAMES: Record<string, string> = {
  "J01": "Antibacterianos para uso sistémico",
  "J01C": "Penicilinas",
  "J01D": "Cefalosporinas",
  "J01F": "Macrólidos",
  "J01M": "Quinolonas",
  "J01A": "Tetraciclinas",
  "J01X": "Otros antibacterianos",
  "J01CR": "Penicilinas combinadas",
  "J01DD": "Cefalosporinas 3a gen.",
  "J01FA": "Macrólidos simples",
  "J01MA": "Fluoroquinolonas",
  "J01CA": "Penicilinas espectro extendido",
  "J01EE": "Sulfonamidas combinadas",
  "J01GB": "Aminoglucósidos",
  "J01XD": "Imidazoles",
  "J01XA": "Glucopéptidos",
  "M01": "Antiinflamatorios",
  "N02": "Analgésicos",
  "N05": "Ansiolíticos",
  "N06": "Antidepresivos",
  "A10": "Antidiabéticos",
  "C10": "Hipolipemiantes",
  "A02": "Antiulcerosos",
  "C07": "Betabloqueantes",
  "C08": "Calcioantagonistas",
  "C09": "IECA/ARA-II",
  "R03": "Antiasmáticos",
};

const METRIC_LABELS: Record<string, string> = {
  "dhd": "DHD (Dosis por Habitante y Día)",
  "ddd": "DDD (Dosis Diaria Definida)",
  "packages": "Envases",
  "amount_pvpiva": "PVP IVA (Importe en Euros)",
};

export function formatEntityKey(key: string, short = false): string {
  const parts = key.split("|");
  if (parts.length < 2) return key;

  const geo = parts[0].trim();
  const atc = parts[1].trim();
  const atcLabel = ATC_NAMES[atc] || atc;

  if (short) return `${geo} > ${atc}`;
  return `${geo} > ${atcLabel} (${atc})`;
}

export function getAtcName(atcCode: string): string {
  return ATC_NAMES[atcCode] || atcCode;
}

export function getMetricLabel(metric: string): string {
  return METRIC_LABELS[metric] || metric.toUpperCase();
}

export { ATC_NAMES, METRIC_LABELS };
