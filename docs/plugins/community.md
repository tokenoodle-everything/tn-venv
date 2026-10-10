# Plugin registry

A directory of every `tn-venv` plugin we know about, with a
quality score. All ratings are 1-5 stars and **all four** must be
filled in for a row to count as reviewed.

```{note}
This registry is **maintained by the tn-venv maintainers** - not
self-assigned by plugin authors. Submit your plugin by opening a
pull request against `docs/index.md` adding a row, or by filing an
issue. See {doc}`../plugins/index` for the contribution rules.
```

## Rating dimensions

Every reviewed plugin gets four ratings, each on a 1-5 star scale:

| Rating | What it measures |
|---|---|
| **Maintenance** | Is the plugin actively kept up with tn-venv releases? Does it have a recent commit history? Does it answer issues? |
| **Stability** | Does the public API stay stable across releases? Are breaking changes documented? Is the test suite passing? |
| **Documentation** | Is there a README? Are `register()` / hooks / payloads documented? Are common-pitfalls covered? |
| **Adoption** | Is the plugin downloaded by many users? Referenced in real projects? |

All four must be filled in for a plugin to be "reviewed". A row
without all four ratings is treated as **unreviewed** and shows up
in the table with an explicit "-" marker.

## Tiers

The four ratings are averaged and mapped to a tier:

| Tier | Color | Average score | Badge |
|---|---|---|---|
| Tier 1 | bronze | 1.0 - 2.0 | ![tier-1](https://img.shields.io/badge/tier-1-bronze-C68863) |
| Tier 2 | silver | 2.0 - 3.0 | ![tier-2](https://img.shields.io/badge/tier-2-silver-C0C0C0) |
| Tier 3 | gold | 3.0 - 4.0 | ![tier-3](https://img.shields.io/badge/tier-3-gold-D4AF37) |
| Tier 4 | platinum | 4.0 - 5.0 | ![tier-4](https://img.shields.io/badge/tier-4-platinum-E5E4E2) |

A plugin at **Tier 4** is considered production-grade. We
recommend Tier 3+ for any plugin that ships in a CI environment.

Tier boundaries are **inclusive** at the lower end and
**exclusive** at the upper end. A 2.0 average is Tier 2, a 4.0
average is Tier 4.

## Official Authorized

The **Official Authorized** badge marks a plugin as:

- Maintained by the tn-venv team or a designated maintainer
- Held to the tn-venv contribution standards (CI, tests,
  changelog, docs)
- Reviewed every month for breakage against tn-venv trunk

This badge is **granted only by the tn-venv team**. Plugin authors
do not assign it to themselves. Submitting a PR that adds your own
"official authorized" cell is grounds for rejection; please open
an issue instead and we'll review and grant.

| Plugin | Status |
|---|---|
| `tn-venv-gui` | Official Authorized |

## Registry

All ratings are 1-5 stars. A "-" means "not reviewed" (the plugin
isn't listed as a failure - it's simply too new or too obscure
to have been evaluated).

| Plugin | Author | Repository | Maintenance | Stability | Documentation | Adoption | Tier | Reviewed |
|---|---|---|---|---|---|---|---|---|
| `tn-venv-gui` | Tokenoodle-Everything | [repo](https://github.com/tokenoodle-everything/tn-venv-gui) | 5/5 | 5/5 | 3/5 | 2/5 | Tier 3 (gold) | 2026-10-10 |

### How to read the row

- **Maintenance 4/5** means "actively maintained, recent
  releases, responsive".
- **Stability 5/5** means "API stable across the last two minor
  versions, all tests pass on the latest tn-venv".
- **Documentation 5/5** means "README, API docs, recipes, and a
  CHANGELOG are all present and accurate".
- **Adoption 4/5** means "downloaded regularly, referenced in
  production projects".

The **Tier** column shows the average across all four. The
**Reviewed** column shows when the maintainers last evaluated the
plugin against tn-venv trunk.

### Submitting a plugin

To add a plugin row:

1. Open a PR against `docs/plugins/community.md`.
2. Add a single markdown table row in alphabetical order by plugin
   name.
3. The four ratings and the **Reviewed** date are filled in by
   the tn-venv maintainers **after** merging. Pre-filling them is
   grounds for reversion.
4. The **Tier** is computed automatically from the four ratings;
   pre-filling it is also grounds for reversion.

We commit to evaluating new submissions within 14 days. If your
plugin is added to the table with a "-" rating, the maintainers
have not yet reviewed it.

## Shields.io badge snippets

Each row in the registry is generated from a per-plugin Shields.io
URL. The canonical form is:

```markdown
![Maintenance 4/5](https://img.shields.io/badge/maintenance-4%2F5-brightgreen)
![Stability 5/5](https://img.shields.io/badge/stability-5%2F5-brightgreen)
![Documentation 5/5](https://img.shields.io/badge/documentation-5%2F5-brightgreen)
![Adoption 4/5](https://img.shields.io/badge/adoption-4%2F5-brightgreen)
![Tier platinum](https://img.shields.io/badge/tier-platinum-E5E4E2)
![Official](https://img.shields.io/badge/official%20authorized-C0C0C0)
```

The score (`4`/`5`) maps to a colour: `1`-`2` -> red, `3` -> yellow,
`4`-`5` -> brightgreen. Adjust the score in your README or docs
copy to match the row in the registry.

If you maintain a plugin and want to embed its row in your own
README, copy the badge line for the current row. The maintainers
will update the registry row at the start of each monthly review
cycle; your README badges will go stale until you re-sync.

## Monthly selection

Each month the tn-venv maintainers pick:

- **Plugin of the Month** - one plugin per month, prominently
  highlighted in the next release notes.
- **Rising Plugin** - one plugin that crossed a tier boundary or
  showed significant improvement since the previous month.
- **Most Discussed** - the plugin that generated the most issue /
  discussion traffic in the last 30 days.

> No entries yet. The first selection will appear in the November
> 2026 cycle. The criteria and judging process are documented
> below.

### Selection criteria

A plugin is eligible for **Plugin of the Month** when:

1. It is registered in the table above with all four ratings
   filled in.
2. It is **not** a Starter plugin (Tier 1) - the bar is Tier 2+.
3. Its maintainer has shipped at least one release in the last 30
   days.
4. It does not have any open "bug" or "compatibility" issue older
   than 14 days.

**Rising Plugin** is awarded to the row whose tier *increased*
since the previous month, or whose adoption metric jumped by one
full star.

**Most Discussed** is computed automatically from the
`tn-venv/tn-venv-gui` issues and discussions APIs. Owners of
ineligible plugins (no rating, abandoned, etc.) are not considered.

### Past winners

| Month | Plugin of the Month | Rising Plugin | Most Discussed |
|---|---|---|---|
| _no selections yet_ | | | |

Past winners are kept permanently so the table reads as a
historical record.

## How to get your plugin reviewed faster

Practical advice for plugin authors:

- **Add a CI badge** to your README - reviewers check this first.
- **Pin your plugin's `tn-venv` upper bound** to a tested version
  range (e.g. `tn-venv>=1.0,<2.0`). Floating-version deps get
  deprioritized for review.
- **Run `tn-venv --list-plugins` in your test suite** - the loader
  must succeed for your plugin to be considered "stable".
- **Document your public hooks in a `docs/` directory** - reviewers
  can tick off Documentation stars faster.
- **Tag releases with `@version`** - the registry cross-checks
  that you follow tn-venv's release tagging convention.

## Removing a plugin

A plugin is removed from the registry when:

- It has not released in 12 months AND the maintainer is
  unreachable.
- It ships code that actively breaks tn-venv (e.g. monkey-patches
  internals in a way that survives a refactor and corrupts state).
- Its maintainer asks to be removed.

Removals are announced in the next release notes. Plugins removed
for inactivity can be re-added by re-establishing maintenance
and opening a PR.
