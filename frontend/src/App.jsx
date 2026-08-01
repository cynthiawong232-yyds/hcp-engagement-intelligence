import {
  LADDER,
  DATA_FACTS,
  TREND_YEARS,
  PLACEBO_LEVELS,
  PLACEBO_GROWTH,
  BALANCE,
  DECILES,
  POWER,
  LIMITATIONS,
  NEXT,
} from "./data.js";

const REPO = "https://github.com/cynthiawong232-yyds/hcp-engagement-intelligence";

const SECTIONS = [
  ["finding", "The finding"],
  ["problem", "Why it is hard"],
  ["data", "The data"],
  ["trends", "Parallel trends"],
  ["matching", "Matching"],
  ["uplift", "The uplift failure"],
  ["holdout", "The holdout"],
  ["limits", "Limitations"],
];

function Section({ id, eyebrow, title, lede, children }) {
  return (
    <section id={id} className="section">
      <div className="section-head">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {children}
    </section>
  );
}

function Ladder() {
  const max = Math.max(...LADDER.map((d) => d.value));
  return (
    <div className="ladder">
      {LADDER.map((d) => (
        <div className="ladder-row" key={d.label}>
          <div className="ladder-label">
            <span className="ladder-name">{d.label}</span>
            <code className="mod">{d.module}</code>
          </div>
          <div className="ladder-track">
            <div
              className={`ladder-bar tone-${d.tone}`}
              style={{ width: `${(d.value / max) * 100}%` }}
            />
            <span className="ladder-value">{d.value.toFixed(1)}</span>
          </div>
          <p className="ladder-note">{d.note}</p>
        </div>
      ))}
      <div className="ladder-row failed">
        <div className="ladder-label">
          <span className="ladder-name">per-doctor uplift ranking</span>
          <code className="mod">hei.uplift</code>
        </div>
        <div className="ladder-track">
          <span className="failed-tag">FAILED</span>
        </div>
        <p className="ladder-note">Qini area negative, worse than random</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <a className="skip" href="#finding">
        Skip to the finding
      </a>

      <header className="hero">
        <div className="wrap">
          <p className="kicker">Causal inference on real public data</p>
          <h1>
            Does pharmaceutical promotion actually cause doctors to prescribe
            more?
          </h1>
          <p className="sub">
            Four causal methods, an uplift model that fails its own evaluation,
            and the randomised experiment that would fix it. Every number on
            this page is printed by a script in the repository.
          </p>
          <div className="hero-actions">
            <a className="btn primary" href={REPO}>
              Read the code
            </a>
            <a className="btn" href="#finding">
              The finding
            </a>
          </div>
        </div>
      </header>

      <nav className="nav" aria-label="Sections">
        <div className="wrap nav-inner">
          {SECTIONS.map(([id, label]) => (
            <a key={id} href={`#${id}`}>
              {label}
            </a>
          ))}
        </div>
      </nav>

      <main className="wrap">
        <Section
          id="finding"
          eyebrow="The headline"
          title="The average effect is real and small. The per-doctor effect is not recoverable at all."
          lede="The obvious comparison says promotion nearly doubles prescribing. Almost all of that is the sales reps' own targeting decisions, not the promotion. Each correction below removes a different piece of that."
        >
          <Ladder />
          <div className="callout">
            <p>
              <strong>
                Roughly 5 to 12 extra prescriptions per doctor per year.
              </strong>{" "}
              That range is the honest answer, and it is an upper bound. The
              second finding is the one that matters more: the model cannot say{" "}
              <em>which</em> doctors drive it. That is why this project ends
              with an experiment design instead of a targeting list.
            </p>
          </div>
        </Section>

        <Section
          id="problem"
          eyebrow="The confounding"
          title="Reps are sent to the doctors who already prescribe the most"
          lede="In prescription drugs, three different people do what one person usually does. The doctor chooses the drug, the patient takes it, the insurer pays for it. So pharmaceutical companies market to doctors one at a time, mostly by sending a sales representative to the office with lunch."
        >
          <div className="cards">
            <div className="card">
              <h3>The choice is not random</h3>
              <p>
                Reps visit high prescribers on purpose. That is good
                salesmanship and it is fatal to measurement, because the thing
                that predicts who gets visited is the same thing that predicts
                the outcome.
              </p>
            </div>
            <div className="card">
              <h3>So promoted doctors always look better</h3>
              <p>
                Whether or not the visit did anything. Removing that gap is
                what this entire project is built to do, and the honest result
                is that it can only be partly removed.
              </p>
            </div>
            <div className="card">
              <h3>The design forces one shared cutoff</h3>
              <p>
                Treated doctors had no payments from 2019 to 2021 and a first
                payment in 2022. Controls were never paid. Anyone already
                promoted is excluded, because they have no clean before.
              </p>
            </div>
          </div>
        </Section>

        <Section
          id="data"
          eyebrow="Real, public, free"
          title="No synthetic data anywhere"
          lede="CMS Open Payments records every promotional contact with a named doctor. CMS Medicare Part D Prescribers records how much each doctor prescribed. They join on NPI, the doctor's permanent national ID. These are the open analogs of Veeva CRM and IQVIA Xponent."
        >
          <div className="stats">
            {DATA_FACTS.map((s) => (
              <div className="stat" key={s.label}>
                <span className="stat-value">{s.value}</span>
                <span className="stat-label">{s.label}</span>
              </div>
            ))}
          </div>
          <div className="cards two">
            <div className="card">
              <h3>Medicare cannot pay for weight-loss drugs</h3>
              <p>
                It is barred by statute. So Zepbound and Saxenda have plenty of
                promotional payments and no prescribing data. The treatment
                exists, the outcome does not. Found by measuring, not assuming.
              </p>
            </div>
            <div className="card">
              <h3>A drug launch is only half a natural experiment</h3>
              <p>
                Mounjaro launched in 2022, so its payments are exactly zero
                beforehand, which looks ideal. But nobody prescribed it
                beforehand either, so both groups sit at zero through the whole
                pre-period and difference-in-differences collapses back into
                the biased comparison it was meant to replace.
              </p>
            </div>
          </div>
        </Section>

        <Section
          id="trends"
          eyebrow="The assumption nearly everyone asserts"
          title="The parallel trends test, and it does not cleanly pass"
          lede="Difference-in-differences uses the control group's change as a stand-in for what the treated group would have done anyway. That substitution is only legal if the two groups would have moved together. With three pre-treatment years, that can be tested rather than claimed."
        >
          <div className="table-wrap">
            <table>
              <caption>
                Mean prescriptions by year. Balanced panel of 56,544 doctors:
                2,207 treated, 16,321 control. Parallel trends means the gap
                column stays the same size.
              </caption>
              <thead>
                <tr>
                  <th>Year</th>
                  <th className="num">Treated</th>
                  <th className="num">Control</th>
                  <th className="num">Gap</th>
                  <th className="num">Gap grew by</th>
                  <th>Period</th>
                </tr>
              </thead>
              <tbody>
                {TREND_YEARS.map((r) => (
                  <tr key={r.year} className={r.post ? "row-post" : ""}>
                    <td>{r.year}</td>
                    <td className="num">{r.treated.toFixed(1)}</td>
                    <td className="num">{r.control.toFixed(1)}</td>
                    <td className="num">{r.gap.toFixed(1)}</td>
                    <td className="num">
                      {r.grew === null ? "—" : r.grew.toFixed(1)}
                    </td>
                    <td className="muted">
                      {r.post ? "after promotion" : "no promotion yet"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="callout warn">
            <p>
              In 2021, before any of these doctors had received a payment, the
              future-treated group already prescribed 22.7 more. Nothing had
              happened yet.
            </p>
          </div>

          <h3 className="sub-head">The placebo test</h3>
          <p className="body">
            A placebo period is one where no promotion happened. Run the
            identical calculation on it and the answer should be zero. It is a
            fake test with a known answer. If the method finds an effect where
            there was none, it cannot be trusted where there was one.
          </p>

          <div className="table-grid">
            <div className="table-wrap">
              <table>
                <caption>On the level scale, in prescriptions</caption>
                <thead>
                  <tr>
                    <th>Period</th>
                    <th className="num">Treated</th>
                    <th className="num">Control</th>
                    <th className="num">DiD</th>
                  </tr>
                </thead>
                <tbody>
                  {PLACEBO_LEVELS.map((r) => (
                    <tr key={r.period} className={r.real ? "row-post" : ""}>
                      <td>
                        {r.period}
                        <span className={`tag ${r.real ? "tag-real" : ""}`}>
                          {r.real ? "real" : "placebo"}
                        </span>
                      </td>
                      <td className="num">{r.treated.toFixed(1)}</td>
                      <td className="num">{r.control.toFixed(1)}</td>
                      <td className="num strong">{r.diff.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={4}>
                      largest placebo 7.0 · real 12.2 ·{" "}
                      <strong>ratio 1.7x</strong>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="table-wrap">
              <table>
                <caption>On the growth scale, in percent</caption>
                <thead>
                  <tr>
                    <th>Period</th>
                    <th className="num">Treated</th>
                    <th className="num">Control</th>
                    <th className="num">Diff</th>
                  </tr>
                </thead>
                <tbody>
                  {PLACEBO_GROWTH.map((r) => (
                    <tr key={r.period} className={r.real ? "row-post" : ""}>
                      <td>
                        {r.period}
                        <span className={`tag ${r.real ? "tag-real" : ""}`}>
                          {r.real ? "real" : "placebo"}
                        </span>
                      </td>
                      <td className="num">{r.treated.toFixed(1)}%</td>
                      <td className="num">{r.control.toFixed(1)}%</td>
                      <td className="num strong">{r.diff.toFixed(1)}pp</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={4}>
                      largest placebo 2.5pp · real 4.6pp ·{" "}
                      <strong>ratio 1.9x</strong>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <div className="callout warn">
            <p>
              <strong>The scale changes the story, so both are reported.</strong>{" "}
              In prescription counts the groups look clearly divergent. In
              growth rates they moved almost identically before treatment, and
              much of the widening gap was arithmetic from the treated group
              starting larger. On neither scale is the real effect more than
              about twice a fake one. You would want five or ten times.
            </p>
          </div>
        </Section>

        <Section
          id="matching"
          eyebrow="Propensity score matching"
          title="It works, and it works because the model is bad"
          lede="Judged on covariate balance rather than AUC. Nine unbalanced covariates become zero, and all 10,411 treated doctors find a partner."
        >
          <div className="table-wrap">
            <table>
              <caption>
                Standardised mean difference before and after matching. Anything
                past 0.10 counts as imbalanced.
              </caption>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th className="num">SMD before</th>
                  <th className="num">SMD after</th>
                </tr>
              </thead>
              <tbody>
                {BALANCE.map((r) => (
                  <tr key={r.feature}>
                    <td>
                      <code>{r.feature}</code>
                    </td>
                    <td className="num bad-num">{r.before.toFixed(3)}</td>
                    <td className="num good-num">{r.after.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>
                    imbalanced features: <strong>9 before</strong> →{" "}
                    <strong>0 after</strong> · 10,411 of 10,411 treated doctors
                    matched
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div className="callout">
            <p>
              Treated doctors average a 0.170 probability of promotion and
              controls 0.147. Almost identical.{" "}
              <strong>
                In propensity score matching, strong prediction is evidence the
                groups cannot be compared at all
              </strong>
              , which is backwards from ordinary machine learning. A model that
              predicted well would push the groups apart and leave no pairs to
              form.
            </p>
          </div>
        </Section>

        <Section
          id="uplift"
          eyebrow="The result this project is built around"
          title="The uplift model is right on average and useless in practice"
          lede="A T-learner: one XGBoost model trained on promoted doctors, another on unpromoted, uplift is the difference. Predictions are cross-fitted over five folds, so no doctor is ever scored by a model that saw them. Without that step the gap between a memory and a guess looks exactly like uplift."
        >
          <div className="table-wrap">
            <table>
              <caption>
                Doctors ranked by predicted uplift, then checked against what
                really happened. A model that works shows observed uplift
                falling as you go down the table.
              </caption>
              <thead>
                <tr>
                  <th className="num">Decile</th>
                  <th className="num">n</th>
                  <th className="num">Predicted</th>
                  <th className="num">Observed</th>
                </tr>
              </thead>
              <tbody>
                {DECILES.map((r) => (
                  <tr
                    key={r.decile}
                    className={
                      r.decile === 10 || r.decile === 1 ? "row-mark" : ""
                    }
                  >
                    <td className="num">{r.decile}</td>
                    <td className="num muted">{r.n.toLocaleString()}</td>
                    <td className="num">{r.predicted.toFixed(1)}</td>
                    <td className="num strong">{r.observed.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4}>
                    top decile minus bottom decile:{" "}
                    <strong className="bad-num">-41.2 Rx</strong> · Qini area
                    above random: <strong className="bad-num">-43,510</strong>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="split">
            <div className="verdict good">
              <h3>The average</h3>
              <p className="verdict-value">Fine</p>
              <p>
                Mean predicted uplift is 7.4 Rx, inside the causal range of 5.2
                to 11.7.
              </p>
            </div>
            <div className="verdict bad">
              <h3>The ordering</h3>
              <p className="verdict-value">Worthless</p>
              <p>
                The doctors ranked lowest responded the most. It cannot say
                which doctors respond.
              </p>
            </div>
          </div>

          <div className="refusal">
            <p className="refusal-tag">NONE ISSUED</p>
            <p>
              This section would normally hand over a list of doctors to visit.{" "}
              <strong>
                It is withheld, on purpose, because the model failed its own
                evaluation.
              </strong>{" "}
              Shipping a targeting list from a ranking that scores worse than
              random would move real sales-rep time on the strength of noise.
              The honest deliverable is the refusal plus the reason.
            </p>
            <p className="muted">
              Causes, in order of size: only 2,207 treated doctors to learn
              variation from; an effect of 5 to 12 Rx sitting inside year-to-year
              noise with a standard deviation near 64; and the confounding above
              contaminating what remains.
            </p>
          </div>
        </Section>

        <Section
          id="holdout"
          eyebrow="Designed and priced, deliberately not run"
          title="The experiment that would settle it"
          lede="Randomisation removes the confounding at the source instead of repairing it afterwards. No parallel trends assumption, no worry about whether enough was controlled for. What this project produces is the design: how many doctors, what it costs, and which questions are too small to answer at any price."
        >
          <div className="table-wrap">
            <table>
              <caption>
                80% power, 5% significance, two-sided, with a 1.35x design
                effect for territory-level clustering.
              </caption>
              <thead>
                <tr>
                  <th className="num">Effect to detect</th>
                  <th className="num">% of mean</th>
                  <th className="num">n/arm, levels</th>
                  <th className="num">n/arm, change</th>
                  <th className="num">Cost</th>
                </tr>
              </thead>
              <tbody>
                {POWER.map((r) => (
                  <tr key={r.pct} className={r.feasible ? "" : "row-dead"}>
                    <td className="num">{r.delta.toFixed(1)} Rx</td>
                    <td className="num muted">{r.pct}</td>
                    <td className="num">{r.levels.toLocaleString()}</td>
                    <td className="num strong">{r.change.toLocaleString()}</td>
                    <td className="num">
                      {r.cost ?? (
                        <span className="dead-tag">more doctors than exist</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="cards two">
            <div className="card accent">
              <h3>One analysis decision cuts the sample by 78%</h3>
              <p>
                Analysing the holdout as a before/after change rather than an
                after-only comparison makes each doctor their own control.
                Everything permanent about them cancels, and the noise drops
                from 138 to 64. Because that number is squared in the formula,
                the same budget buys four times the power. It has to be decided
                in advance.
              </p>
            </div>
            <div className="card accent">
              <h3>The answer an executive needs is the last row</h3>
              <p>
                A 1% lift would need 553,737 doctors per arm, which is more than
                exist. Telling someone that before the budget is approved is
                worth more than any model here. The smallest detectable effect
                with this population is 2.1 Rx, needing 19,199 per arm at about
                $36.8M in forgone sales, reading in two to three quarters.
              </p>
            </div>
          </div>
          <p className="body">
            The holdout is sized here for the <strong>average</strong> effect.
            Sizing it to recover the per-doctor effect, the thing that actually
            failed, is a larger calculation and a larger number. That is the
            next piece of work, not a solved problem.
          </p>
        </Section>

        <Section
          id="limits"
          eyebrow="Stated here rather than discovered by a reader"
          title="Limitations"
        >
          <div className="limits">
            {LIMITATIONS.map((l) => (
              <div className="limit" key={l.title}>
                <h3>{l.title}</h3>
                <p>{l.body}</p>
              </div>
            ))}
          </div>

          <h3 className="sub-head">What I would do differently at scale</h3>
          <div className="limits">
            {NEXT.map((l) => (
              <div className="limit next" key={l.title}>
                <h3>{l.title}</h3>
                <p>{l.body}</p>
              </div>
            ))}
          </div>
        </Section>
      </main>

      <footer className="footer">
        <div className="wrap">
          <p>
            Built on CMS Open Payments and Medicare Part D Prescribers, both
            public. Deliberately generic: no company or job is named anywhere in
            the repository.
          </p>
          <a className="btn primary" href={REPO}>
            View the source on GitHub
          </a>
        </div>
      </footer>
    </>
  );
}
