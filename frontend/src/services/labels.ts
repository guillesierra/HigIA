const ATC_NAMES: Record<string, string> = {
  "J01": "Antibacterianos para uso sistemico",
  "J01C": "Penicilinas",
  "J01D": "Cefalosporinas",
  "J01F": "Macrolidos",
  "J01M": "Quinolonas",
  "J01A": "Tetraciclinas",
  "J01X": "Otros antibacterianos",
  "J01CR": "Penicilinas combinadas",
  "J01DD": "Cefalosporinas 3a gen.",
  "J01FA": "Macrolidos simples",
  "J01MA": "Fluoroquinolonas",
  "J01CA": "Penicilinas espectro extendido",
  "J01EE": "Sulfonamidas combinadas",
  "J01GB": "Aminoglucosidos",
  "J01XD": "Imidazoles",
  "J01XA": "Glucopeptidos",
  "M01": "Antiinflamatorios",
  "N02": "Analgesicos",
  "N05": "Ansioliticos",
  "N06": "Antidepresivos",
  "A10": "Antidiabeticos",
  "C10": "Hipolipemiantes",
  "A02": "Antiulcerosos",
  "C07": "Betabloqueantes",
  "C08": "Calcioantagonistas",
  "C09": "IECA/ARA-II",
  "R03": "Antiasmaticos",
};

const METRIC_LABELS: Record<string, string> = {
  "dhd": "DHD (Dosis por Habitante y Dia)",
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
