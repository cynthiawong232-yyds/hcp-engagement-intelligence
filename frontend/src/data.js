// Every number here is printed by the scripts in src/hei/ and was reproduced
// by rerunning them against data/processed/panel.parquet. Nothing is rounded
// by hand and nothing is estimated. The module each number comes from is
// named next to it so a reader can check it.

export const LADDER = [
  {
    label: "all promoted vs all unpromoted",
    value: 56.5,
    module: "hei.confounding",
    note: "the number a dashboard reports",
    tone: "bad",
  },
  {
    label: "naive, on a clean sample",
    value: 29.7,
    module: "hei.matching",
    note: "excludes doctors already promoted before the cutoff",
    tone: "bad",
  },
  {
    label: "propensity score matching",
    value: 10.0,
    module: "hei.matching",
    note: "groups made comparable on what we can measure",
    tone: "ok",
  },
  {
    label: "difference-in-differences",
    value: 11.7,
    module: "hei.confounding",
    note: "growth compared, not size",
    tone: "ok",
  },
  {
    label: "PSM + DiD",
    value: 8.1,
    module: "hei.matching",
    note: "both corrections at once, the most defensible",
    tone: "ok",
  },
  {
    label: "trend-adjusted",
    value: 5.2,
    module: "hei.trends",
    note: "pre-existing divergence removed",
    tone: "ok",
  },
];

export const DATA_FACTS = [
  { value: "24.9M", label: "payment rows scanned, 2019 to 2022" },
  { value: "2.0M", label: "rows kept for GLP-1 and SGLT2 drugs" },
  { value: "487,744", label: "doctor-year rows in the panel" },
  { value: "206,024", label: "distinct doctors" },
];

// hei.trends, balanced panel: 56,544 doctors, 2,207 treated, 16,321 control
export const TREND_YEARS = [
  { year: 2019, treated: 53.7, control: 43.9, gap: 9.8, grew: null, post: false },
  { year: 2020, treated: 80.1, control: 64.4, gap: 15.7, grew: 5.9, post: false },
  { year: 2021, treated: 112.6, control: 90.0, gap: 22.7, grew: 7.0, post: false },
  { year: 2022, treated: 152.6, control: 117.8, gap: 34.8, grew: 12.2, post: true },
];

export const PLACEBO_LEVELS = [
  { period: "2019 → 2020", treated: 26.4, control: 20.5, diff: 5.9, real: false },
  { period: "2020 → 2021", treated: 32.6, control: 25.6, diff: 7.0, real: false },
  { period: "2021 → 2022", treated: 39.9, control: 27.8, diff: 12.2, real: true },
];

export const PLACEBO_GROWTH = [
  { period: "2019 → 2020", treated: 49.2, control: 46.8, diff: 2.5, real: false },
  { period: "2020 → 2021", treated: 40.7, control: 39.7, diff: 1.0, real: false },
  { period: "2021 → 2022", treated: 35.5, control: 30.9, diff: 4.6, real: true },
];

export const BALANCE = [
  { feature: "n_drugs", before: 0.243, after: 0.001 },
  { feature: "cost_total", before: 0.239, after: -0.003 },
  { feature: "rx_total", before: 0.218, after: -0.0 },
  { feature: "beneficiaries", before: 0.189, after: -0.005 },
  { feature: "rx_sglt2", before: 0.186, after: 0.001 },
  { feature: "sp_Nurse Practitioner", before: 0.142, after: 0.01 },
  { feature: "sp_Pharmacist", before: -0.139, after: 0.0 },
  { feature: "sp_Internal Medicine", before: -0.102, after: 0.009 },
  { feature: "sp_Cardiology", before: 0.102, after: -0.01 },
];

export const DECILES = [
  { decile: 10, n: 1853, predicted: 65.0, observed: 48.8 },
  { decile: 9, n: 1853, predicted: 24.0, observed: 22.8 },
  { decile: 8, n: 1853, predicted: 14.8, observed: 13.8 },
  { decile: 7, n: 1852, predicted: 9.9, observed: 11.9 },
  { decile: 6, n: 1853, predicted: 6.5, observed: 14.3 },
  { decile: 5, n: 1853, predicted: 3.6, observed: 22.6 },
  { decile: 4, n: 1852, predicted: 0.6, observed: 10.5 },
  { decile: 3, n: 1853, predicted: -2.7, observed: 11.3 },
  { decile: 2, n: 1853, predicted: -8.1, observed: 10.6 },
  { decile: 1, n: 1853, predicted: -39.4, observed: 90.0 },
];

export const POWER = [
  { delta: 17.0, pct: "20%", levels: 1384, change: 300, cost: "$4.6M", feasible: true },
  { delta: 8.5, pct: "10%", levels: 5537, change: 1200, cost: "$9.2M", feasible: true },
  { delta: 4.3, pct: "5%", levels: 22149, change: 4800, cost: "$18.4M", feasible: true },
  { delta: 2.1, pct: "2.5%", levels: 88598, change: 19199, cost: "$36.8M", feasible: true },
  { delta: 0.9, pct: "1%", levels: 553737, change: 119995, cost: null, feasible: false },
];

export const LIMITATIONS = [
  {
    title: "Medicare only",
    body: "Commercial insurance is absent, so every volume figure understates a doctor's true prescribing.",
  },
  {
    title: "Small-count suppression",
    body: "Part D deletes any prescriber-drug row under 11 claims for privacy. Low-volume prescribing is missing, not zero, and the two cannot be told apart. This truncates exactly where small effects would appear.",
  },
  {
    title: "Parallel trends does not cleanly hold",
    body: "So every estimate on this page is an upper bound rather than a point estimate.",
  },
  {
    title: "The balanced panel selects",
    body: "Requiring a doctor to appear in all four years favours consistent prescribers and shrinks the sample from 206,024 to 56,544.",
  },
  {
    title: "Promotion is a binary",
    body: "Defined as one payment or more. The threshold is a decision, not a fact, and the analysis is repeated at three or more.",
  },
  {
    title: "Revenue per prescription is assumed",
    body: "Used only to price the experiment. Net of rebates it would be roughly a third of the $900 figure used, so the costs read as an upper bound.",
  },
];

export const NEXT = [
  {
    title: "A staggered-adoption estimator",
    body: "The single-cutoff design discards every doctor promoted before 2022. Callaway and Sant'Anna's estimator uses them properly and would recover a lot of sample.",
  },
  {
    title: "Territory-level randomisation from the start",
    body: "Doctors in one practice share protocols, so individual randomisation leaks. The design effect is assumed here at 1.35 and should be measured.",
  },
  {
    title: "Monthly rather than annual data",
    body: "Part D is annual, which is too coarse to see how quickly prescribing responds to a visit, or whether the effect decays.",
  },
  {
    title: "Dose, not a binary",
    body: "Fourteen visits and one visit are both promoted here. A dose-response curve is the more useful commercial object, and it is what tells you when to stop spending.",
  },
];
