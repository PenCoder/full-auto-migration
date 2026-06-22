# Migration Wizard — Project Walkthrough

A concise, step-by-step account of what this project is, why it matters, how it was managed,
and — concretely — how far it moved beyond the proof of concept it started from. Framed for a
project-management and digital-sovereignty review; technical detail is kept as supporting
evidence, not the main narrative.

---

## 1. The problem: digital sovereignty, not just convenience

Digital sovereignty is the capacity to exercise meaningful control over your own digital
infrastructure, data flows, and computational processes — autonomy, control, transparency
(Floridi, 2020; Pohle & Thiel, 2020). Operating systems sit at the center of this: Windows 11
integrates telemetry that cannot be fully disabled, and users have no way to verify or
constrain what it collects.

This is not a hypothetical concern. Survey data shows a clear preference–behaviour gap in
Europe: 63.2% of organisations rate open-source software as critical for sovereignty, 47.4%
cite reducing dependency on non-EU vendors as a strategic priority — yet Windows still holds
67.75% desktop market share (Wire, 2025; StatCounter, 2025). The gap is not a lack of will;
it's migration barriers — technical complexity, fear of data loss, and uncertainty about
whether familiar apps have a Linux equivalent.

**This project's premise:** if the barrier is technical complexity, the fix is a tool that
removes it — a semi-automated migration framework that lets a non-technical user move from
Windows 11 to Linux Mint with their data intact and their workflow preserved.

---

## 2. Baseline: the proof of concept this project builds on

This is not a from-scratch project. It extends an existing seminar proof of concept —
[`PenCoder/semi-auto-migration`](https://github.com/PenCoder/semi-auto-migration) — the same
codebase the term paper "Digital Sovereignty Through Semi-Automated Migration from Windows to
Linux" describes and evaluates. The comparison below is against that actual repository, not a
paraphrase of it.

| Aspect | Proof of concept (original repo) | This project | Change |
|---|---|---|---|
| App mappings | **25** entries | **238** entries | **9.5×** |
| Source LOC | **4,031** | **17,467** | **4.3×** |
| Automated tests | **0** | **192** functions, 3,595 LOC | 0 → 192 |
| GUI framework | Tkinter + ttkbootstrap | PySide6 (Qt) | rewritten |
| App-matching | One stage: substring containment only | Three stages: exact → fuzzy (confidence-floored) → live Repology check | 1 → 3 stages |
| Mode system | UI-only; gates one thing (is a scan mandatory) | Gates 3 pipeline decisions via one shared, verified module used by both the GUI and the CLI | 1 → 3 governed decisions |
| Settings (wallpaper/theme) migration | Not present | Implemented | new capability |
| Desktop shortcuts | Not present | Implemented, with full undo | new capability |
| Reset / undo a restore | Not present | Implemented (files, shortcuts, settings, opt-in apps) | new capability |
| Completeness scoring | None — restore just logs pass/fail | Sovereignty Score + JSON/Markdown/HTML report | new capability (self-devised metric — see §6) |
| Packaging | Linux only, one binary | Both platforms; Linux binary auto-embeds into every Windows-built bundle | Linux-only → cross-platform |
| `apt-get install` reliability | One atomic batch call, no fallback, no timeout, failures silently logged and ignored | Per-package fallback + 120s timeout | defect inherited from baseline, found and fixed |

**One nuance kept precise rather than overstated:** the original explicitly documents its CLI
as "primarily intended for development, testing, and experimentation," not as something meant
to match the GUI. The Qt/CLI parity *claim* (and its fix) belongs to this Praktikum's own
exposé, not to a promise the proof of concept made and broke.

---

## 3. Project management framing

### Objective
Reduce the technical barriers to OS-level sovereignty restoration while preserving user
control, data integrity, and workflow continuity — the same research question the original
term paper posed, now pursued with measurable targets instead of qualitative goals.

### Measurable objectives (defined at project start, status now)

| Objective | Target | Result |
|---|---|---|
| O1 — Reduce manual steps | ≤ 3 user interactions in guided mode | **3** |
| O2 — App mapping coverage | ≥ 80% of top-50 Windows apps | **238 entries**, top-50 confirmed |
| O3 — File integrity after restore | ≥ 95% pass SHA-256 verification | **100%** in test runs |
| O4 — Migration completeness | Sovereignty Score ≥ 85% | Implemented, scored on real runs |
| O5 — Qt/CLI parity | Identical mode policy on both interfaces | Achieved, verified by object identity |
| O6 — Cycle time | < 20 min for ≤ 5 GB | **Not met** — real run logged ~30–35 min (see §6) |

### Work breakdown & timeline
Seven work packages, April through the presentation date: Architecture → Recommendation
Engine → Workflow Integration → Backup Pipeline → Linux Restore → Packaging → Quality & Docs.
A 6-day risk buffer was added ahead of the final presentation to absorb exactly the kind of
issue that live testing did surface (see §6).

### Risk register (selected)

| Risk | Impact | Status |
|---|---|---|
| Packaging fails across platforms | High | Mitigated — both `.exe` and Linux binary build and embed automatically |
| Files restored to wrong location | High | Fixed |
| App recommendations miss niche software | Medium | Mitigated — fuzzy matching + manual override in Expert mode |
| No end-to-end test on physical hardware | Medium | Open — tests currently run against a VM pair, not physical machines |

---

## 4. What the system does (supporting context)

**Windows side:** scan the system → match installed apps to Linux equivalents → choose
files/settings to bring → review the plan → pack everything into one bundle.

**Linux side, one click:** restore the bundle → verify every file by hash → produce a report
with a Sovereignty Score and a clear account of what succeeded, what needs manual follow-up,
and what failed.

Three modes (Guided/Balanced/Expert) trade off automation for control without changing the
underlying pipeline — Guided requires zero decisions after mode selection; only Expert mode
ever performs an online check, and only to confirm a package recommendation already made
locally, never to send user data anywhere.

---

## 5. Addressing the supervisor's review

The exposé review identified four gaps, all from a project-management and conceptual
standpoint rather than implementation depth:

| # | Gap raised | How it was closed |
|---|---|---|
| 1 | Objectives stated qualitatively ("more dynamic strategies") | Replaced with the O1–O6 table above — each objective now has a number and a checkable result |
| 2 | Methodology for Qt/CLI consistency was under-specified | Named the actual mechanism: one shared decision module both interfaces call, rather than describing the goal without the means |
| 3 | Timeline had no contingency | Added a dedicated 6-day risk buffer before the presentation milestone |
| 4 | Evaluation plan listed categories without metrics | Each category now has a defined metric: interaction count (automation), Sovereignty Score (completeness), per-stage timing (performance). Recommendation-quality precision/recall is defined methodologically but explicitly marked as a target, not yet measured — an honest gap rather than an invented number |

One general lesson from this review, independent of any single gap: a project-management
document should describe what *is* true, not what is *intended* to be true. Re-checking gap 2
against the actual codebase found the original claim ("Qt and CLI share one controller") had
been written before it was implemented. It's fixed now, but the takeaway for future status
reporting is to verify claims against the system before writing them down.

---

## 6. Critique — where this project's own claims didn't hold up either

Applying the same scrutiny to this project's own documentation surfaced two further findings,
beyond the four the supervisor raised:

- **O6 (cycle time) is not met.** The target was <20 minutes for ≤5GB; the real, logged restore
  of a 5GB/3,344-file bundle took roughly 30–35 minutes for extraction, restore, and
  verification alone. The exposé's earlier "Achieved" label for O6 has been corrected.
- **Recommendation-quality precision/recall is 0% measured.** The methodology is defined (a
  ~30-app ground-truth set, precision/recall formulas, per-strategy breakdown) but no
  evaluation script has been built or run — the numbers that previously appeared in the exposé
  were estimates, not results, and have been relabeled as targets.
- **The Sovereignty Score formula itself has no external citation.** The *concept* of digital
  sovereignty is grounded in cited literature; the specific scoring formula
  (`integrity_score + openness_bonus`, weighted 15/5, capped at 100) is a metric devised for
  this project, not adapted from prior work. Its arithmetic is real; its weighting is not
  externally validated.

---

## 7. Current status

- **238** curated app mappings (**9.5×** the proof of concept's 25), **192** automated tests
  (the proof of concept had none), **2** platforms packaged for one-click distribution (the
  proof of concept packaged Linux only)
- **5 of 6** measurable objectives (O1–O5) met; O6 is open and corrected rather than claimed
- **100%** Sovereignty Score on the most recent real restore run — on a self-devised metric,
  not an externally validated one
- **Open:** the precision/recall evaluation script, the O6 cycle-time target, and a true
  end-to-end test on physical (non-VM) hardware — all carried forward as named risks rather
  than silently dropped
