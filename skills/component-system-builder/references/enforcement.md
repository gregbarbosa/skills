# Enforcement: the map, the ladder, and the proven rung-5 recipe

Read when: drafting a project's enforcement map (Pass 0, or before artifact 1
in green-field), moving the map inline into the boot file (Pass N+1 / when
writing artifact 4), or building mechanical enforcement (Pass N+2).

## The enforcement map (build this BEFORE any rigidity)

The ladder is universal; the mechanisms are platform-dependent. For each rung
4–6, name the concrete mechanism available on THIS platform, or "none — falls
back to rung N". The map lives **inline in the boot file** from Pass N+1 on;
until the boot file is written, the draft lives in the audit doc. Draft it as
a CURRENT-state snapshot — at Pass 0 mostly "none — falls back", which is
honest — plus a target column for what Pass N+2 will build. Rungs 1–3 are
prose/process by definition and need no rows.

| Rung | Web / Electron / Astro | iOS / macOS (SwiftUI) |
| --- | --- | --- |
| 4 Type surface | closed prop unions, no escape-hatch props | enums over strings, `internal`/`fileprivate`, non-public initializers |
| 5 Lint/CI | ESLint `no-restricted-{syntax,imports}` + stylelint for CSS/`<style>` blocks, docs-check script, CI job | SwiftLint `custom_rules` (regex — same evasion class as web regexes, and inline `swiftlint:disable` cannot be banned; note that residue in the map), docs-check script, `xcodebuild` + warnings-as-errors |
| 6 Hard block | unwritable/ignored paths, alias-only imports, protected build output, `--no-inline-config` | SPM module boundaries (kit = its own package; views literally cannot reach internals). You can only deprecate symbols you OWN — "deprecate banned system APIs" is not a real mechanism; that ban falls back to rung 5 |

Rules that keep the map honest:

- **Regex-over-strings misses computed values on every platform** — template
  literals/concatenation (web), string interpolation (Swift). Cover template
  literals where the AST allows (`TemplateElement` in esquery); explicitly
  list the rest under "checked by review, not tooling."
- Astro ≠ generic web: `.astro` files need `eslint-plugin-astro`;
  client-directive limits are lintable. CSS custom properties are
  *availability*, not enforcement — raw hex inside `<style>` blocks needs
  stylelint (with an Astro/HTML syntax); without it, style rules are prose and
  the map must say so.
- SwiftUI's strongest rung is 6-via-packaging: the kit as its own SPM package
  with `internal` internals beats any lint rule — prefer restructuring over
  regex when the platform offers module boundaries.
- If a rung has no mechanism on the platform, place the rule one rung down —
  never invent enforcement the toolchain can't run.
- **The enforcement config is itself a protected artifact**: name what guards
  it (CI integrity check asserting load-bearing selectors exist,
  `--no-inline-config`, branch protection/CODEOWNERS, edit-deny hooks) — or
  admit it's guarded by prose. "Do not weaken" in a comment is rung 1 guarding
  rung 5.
- Rules the map can't enforce mechanically stay prose, listed in the rules
  skill under "checked by review, not tooling" so nobody assumes CI covers
  them.
- **Rigidity is a dial, not a mandate.** The reference implementation
  (quick-import) runs at maximum; a solo static site may legitimately record
  "rung 6: none — config changes reviewed by the owner." The defect is an
  *undocumented* gap, not a low setting.

## The rung-5 recipe (red-teamed + live-fire verified on quick-import)

Reconstructable from this list alone; `gregbarbosa/quick-import`
(`eslint.config.js`, `scripts/check-component-docs.mjs`,
`.github/workflows/ci.yml`) is the worked example if available.

- `no-restricted-syntax` bans, EACH as `Literal[value=/…/]` **and**
  `TemplateElement[value.raw=/…/]` (template literals are how agents naturally
  write classes): raw palette classes (`bg-blue-500`), **arbitrary-value
  colors** (`bg-[#hex]`, `text-[rgb(…]`, `[color:var(…)]` — the
  "compliant-looking" bypass agents reach for once the palette is banned),
  bracket-hex, banned techniques (`backdrop-blur`), and color literals inside
  `style` objects (layout values in `style` stay legal — views often need
  dynamic sizes). Error messages point at the fix ("add a token to @theme")
  and the skill to read.
- **Deny-by-default topology**: strict rules on the whole renderer/site source
  tree, the kit as a narrow named override — never "strict zones" over
  specific view dirs (a new directory must not exit the system).
- `no-restricted-imports` blocks substrate packages (radix/sonner/CVA),
  relative kit paths, and stray CSS files — views import only the kit's
  public alias.
- Docs-check script requiring STRUCTURAL documentation (a heading, backticked
  name, or `<Name` snippet — a bare word-mention passes vacuously for
  components named `Label`/`Status`), recursing into subdirectories, covering
  `export {…}` lists and default exports.
- Run lint with `--no-inline-config` (kills `eslint-disable` outright) plus a
  CI integrity step that greps the config's load-bearing selectors — weakening
  the enforcement fails loudly instead of being blessed by CI.
- CI runs type-check + lint + docs-check + build on every push; require the
  status check on the main branch where the platform supports it.
- **ALWAYS negative-test new rules** (a scratch file with a violation, deleted
  after — never committed) — a rule that never fires is decoration.

## Enforcement patterns worth copying verbatim

- **Sanctioned-exception**: when a banned technique has one legitimate use,
  name it in the component that owns it ("this is the ONE sanctioned use of
  CSS backdrop blur; window glass is native vibrancy"). A ban with a named
  exception holds; a ban with unnamed exceptions erodes.
- **Lore-in-docs**: every hard-won bug becomes a Pitfalls line in the owning
  component's `.md` ("the `min-w-0` child rules are load-bearing — removing
  them collapsed content to 448px once"). The doc is where the agent looks
  *before* re-breaking it.
