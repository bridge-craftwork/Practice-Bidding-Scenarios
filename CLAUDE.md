# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Practice Bidding Scenarios (PBS) is a bridge bidding training platform that integrates with Bridge Base Online (BBO). Users author bidding scenarios as `.btn` files in `btn/` (the master source), generate practice hands with constraints using dealer language, and practice bidding with robots or partners. The system transforms scenario definitions through a multi-stage pipeline into bidding sheets and BBO-compatible formats. (The `.pbs` format still exists, but only as a generated, distributable artifact in `pbs-release/` — see the pipeline below.)

**Repository home:** this repo lives at `github.com/bridge-craftwork/Practice-Bidding-Scenarios` (transferred from `ADavidBailey/` in 2026; GitHub redirects the old URLs, so stale references keep working). Consumers — the BBO browser extension and Bridge Classroom — read its files at runtime from `raw.githubusercontent.com/bridge-craftwork/Practice-Bidding-Scenarios/main/`. The local working copy is still `~/Practice-Bidding-Scenarios` — the transfer changed only the GitHub URL, not local paths.

### Relationship to the Bridge Play Trainer

The Bridge Play Trainer is a **separate repo** (`~/AI-Bridge-Play-Trainer`, github.com/ADavidBailey/AI-Bridge-Play-Trainer) — a web app for practicing the *play* of hands. The split is **content vs. engine** with a one-way runtime dependency:

- **This repo = content + pipeline**: scenarios, the dealer pipeline, the `coaching/*.pbn` tutorial prose, the `btn/` menu layout, the VS Code extension, BBO integration.
- **AI-Bridge-Play-Trainer = engine + UI**: FastAPI server, web UI, card-play mechanics, scoring, the coaching-marker parser.

At runtime the trainer **reads** this repo's files via `BRIDGE_DATA_ROOT` (default this directory) → `coaching/*.pbn` + `btn/`. It never writes back, and this repo doesn't depend on the trainer. Rule of thumb: anything about a *particular hand or what it teaches* belongs here; anything about *how the app behaves for every hand* belongs in the trainer. The one shared seam is the coaching markers (`[show X]`, `[BID xxx]`, `\S\H\D\C`) — prose authored here, parser in the trainer's `server.py`. See [Bridge Play Trainer.md](Bridge Play Trainer.md) for the full trainer write-up.

### Coaching: staging vs. served (`coaching-curated/` → `coaching/`)

Coaching prose has two directories with a one-way promotion between them:

- **`coaching-curated/`** is the **working/staging** directory. All prose is authored and edited here, and all gates run here (`py/coach.py validate`, `py/suit_quality.py`).
- **`coaching/`** is the **served** directory — the files the trainer actually loads. **Never hand-edit `coaching/`**; it is generated.

Promote with `python3 -P py/promote.py` (run from the project root). It is **gated, not a blind copy**: each scenario is copied over its served counterpart only if it passes the full gate suite (`coach.py validate` structure + suit-quality prose, plus the issue-#29 ordering lint). A scenario that fails any gate is **blocked** (left un-promoted) and reported; the script prints what it promoted, what was already current, and what it blocked, and exits non-zero if anything was blocked. Use `--check` for a dry run, or pass scenario names to restrict the set. Edit prose in `coaching-curated/`, re-run the gate, then promote.

## Active work: deal curation (2026-06)

A curation stage is being built between `filter` and coaching authoring.
Before working on anything touching `bba/`, `bba-curated/`, `coaching/`, or
`py/curate|annotate|select|auction_diff|spiral_auction|coach.py`, read:

- the most recent `bookmark-curation-*.md` (current status + open items)
- `pbn-curation-plan.md` (design) and `bba-curated/README.md` (the
  `{Curate}` block format and the `py/select.py` filter)

Convention/spiral scenarios (e.g. `Spiral_Raises_*`) take a different path and do
**not** use `curate.py` (Layer A). They curate via `py/spiral_auction.py`
(`report` → `generate` → `grade` → `substitute`) plus `py/annotate.py`, then coach via
`py/coach.py` (`packets` → `augment` → `splice`). `spiral_auction.py` is parameterized
via `SPIRAL_SCN` (scenario) and `SPIRAL_SCHEME` (`spiral` | `weinstein`) env vars, with
`SCHEME` also honoring a `convention=weinstein` `.btn` directive; it generates both the
spiral cheapest-step ladder (`Spiral_Raises_Wolpert`) and the
Weinstein 2NT-ask + natural-fit-find scheme (`Spiral_Raises_Weinstein`). `annotate.py`
and `select.py` take the scenario as a positional argument.

## Common Commands

### Development Environment Setup

Required environment variables (add to `~/.zshrc`):
```bash
export WINDOWS_HOST="your-windows-ip"
export WINDOWS_USER="your-windows-username"
export PBS_UNC_PREFIX="\\Mac\Home"  # For Parallels; adjust for your VM
export PBS_BCSCRIPT_PATH="~/Documents/BCScript/2024-11-13"
export PBS_DEALER_PLATFORM="mac"  # or "windows"
```

After setting, run: `source ~/.zshrc`

### VS Code Extension Development

```bash
cd vs-code
npm install
npm run compile      # TypeScript → JavaScript
npm run watch        # Continuous compilation
npm run lint         # ESLint validation
```

### Pipeline Operations

Run from `build-scripts-mac/`:

```bash
# Run all operations on a single scenario
python3 pbs-pipeline-mac.py Smolen "*"

# Run operations from 'bba' to end for all scenarios starting with '1N'
python3 pbs-pipeline-mac.py "1N*" "bba+"

# Run specific operation on a scenario
python3 pbs-pipeline-mac.py "Weak_2_Bids" "pbn"
```

Pipeline operations in order:
1. `dlr` - Extract dealer code from the `.btn` master file
2. `pbs` - Render the `.dlr` into a `.pbs` file in `pbs-test/`
3. `pbn` - Generate hands using dealer
4. `rotate` - Create 4-player rotations (PBN and LIN formats)
5. `bba` - Analyze bidding with Bridge Base Archive
6. `filter` - Filter by auction patterns
7. `filterStats` - Generate statistics
8. `biddingSheet` - Generate PDF bidding sheets

The default `*` order continues past `biddingSheet` with `quiz` (generate quiz PBN/PDF) and `package` (copy artifacts into the Bidding Scenarios hierarchy). The `release` and `release-layout` operations are NOT in the default order — invoke them explicitly; `release` promotes `pbs-test/` → `pbs-release/`.

### Testing

```bash
# Run basic dealer tests
python3 py/test_dealer.py

# Verify hand consistency
python3 py/VerifyDealerConsistency.py

# Compare PBN files
python3 build-scripts-mac/pbn-diff.py file1.pbn file2.pbn
```

## Architecture

### Pipeline Flow

The system follows a linear transformation pipeline:

```
btn file (master scenario definition: dealer code + button metadata)
    ↓ [dlr] Extract dealer code
dlr file (dealer language constraints)
    ↓ [pbs] Render .pbs into pbs-test/  (separate [release] op promotes it to pbs-release/)
pbs file (generated artifact)
    ↓ [pbn] Generate hands via dealer (500 per scenario)
pbn file (Portable Bridge Notation)
    ↓ [rotate] Create 4-player rotations
pbn-rotated & lin-rotated files
    ↓ [bba] Analyze bidding with BBA
bba file (with bidding analysis)
    ↓ [filter] Filter by auction patterns
bba-filtered & bba-filtered-out files
    ↓ [filterStats] Count statistics
bba-summary (hand counts)
    ↓ [biddingSheet] Generate PDFs
bidding-sheets (final output)
```

### Cross-Platform Architecture

The system bridges Mac and Windows environments:

- **Mac**: Python orchestrator, native dealer tool, wkhtmltopdf for PDFs
- **Windows VM**: Windows-only tools (dealer.exe, BBA.exe/bba-cli, Filter.js, SetDealerMulti.js)
- **Communication**: SSH with UNC path mapping, file-based queuing for GUI apps

Drive mappings (Mac → Windows):
- `G:` → GitHub folder (parent of project)
- `P:` → Project root
- `S:` → BCScript folder

### VS Code Extension Architecture

Located in `vs-code/src/`:

- **Extension lifecycle**: [extension.ts](vs-code/src/extension.ts) - Command registration and activation
- **Tree views**: [buttonPanelProvider.ts](vs-code/src/buttonPanelProvider.ts) - Hierarchical scenario display
- **Webview**: [buttonGridProvider.ts](vs-code/src/buttonGridProvider.ts) - Interactive button grid
- **Current scenario**: [currentScenarioProvider.ts](vs-code/src/currentScenarioProvider.ts) - Focused scenario with artifacts
- **Parser**: [pbsParser.ts](vs-code/src/pbsParser.ts) - PBS file parsing logic
- **Pipeline runner**: [pipelineRunner.ts](vs-code/src/pipelineRunner.ts) - Command execution

Extension provides:
- Syntax highlighting for PBS, DLR, and PBN formats
- Tree view and button grid for scenario navigation
- Pipeline commands accessible via editor title menu
- File watchers for real-time UI updates

### Directory Structure

**Input/Source:**
- `btn/` - Scenario definitions with button metadata (`.btn` master files — the single source of truth)
- `script/` - Reusable dealer language fragments and macros
- `-PBS.txt` - Master configuration listing all scenarios with section organization

**Generated (Intermediate):**
- `dlr/` - Extracted dealer code
- `pbs-test/` - `.pbs` files rendered from `.dlr` by the `pbs` operation
- `pbs-release/` - Distributable `.pbs` files promoted from `pbs-test/` by the separate `release` operation
- `pbn/` - Bridge Portable Notation files (~500 hands each)
- `pbn-rotated-for-4-players/` - Rotated PBN for 4-player practice
- `lin-rotated-for-4-players/` - LIN format for BBO
- `bba/` - Bridge Base Archive with bidding analysis
- `bba-filtered/` - Filtered BBA files by auction pattern
- `bba-filtered-out/` - BBA files that were filtered out
- `bba-summary/` - Statistics summaries

**Generated (Final Output):**
- `bidding-sheets/` - PDF bidding sheets for practice
- `manifest/` - Pre-built deal-source menu manifests (`manifest-{release,beta,test}.json`), generated by `py/build_manifest.py` via a GitHub Action so the BBO extension / Bridge Classroom build their menu from ONE fetch instead of scanning ~400 `.btn`/`.pbs` files. **Generated — never hand-edit** (see `manifest/README.md`).

**Source Code:**
- `build-scripts-mac/` - Python pipeline orchestration and operations
- `py/` - Python utilities (oneExtract, oneComment, oneSummary, etc.)
- `vs-code/` - TypeScript VS Code extension
- `js/` - JavaScript for BBO automation

**Configuration:**
- `GIB/` - GIB convention card definitions
- `bbsa/` - Bridge Base Scenario Archive
- `.vscode/` - VS Code workspace settings

### Key Python Modules

Core utilities in `py/`:
- `oneExtract.py` - PBS → DLR extraction
- `oneComment.py` - Adds analysis comments to PBN
- `oneSummary.py` - Generates BBA summaries
- `handPatterns.py` - Hand pattern analysis
- `getBBA.py` - BBA file processing

Pipeline operations in `build-scripts-mac/operations/`:
- Modular operation functions registered in `OPERATIONS` dict
- Each operation is independent and re-runnable
- Operations use config.py for paths and settings

### Data Formats

1. **BTN (Button / master scenario)**: The authored source format — combines dealer constraints with button metadata for BBO integration. Lives in `btn/`; everything else is derived from it.
2. **PBS (Practice Bidding Scenario)**: Generated, distributable rendering of a `.btn` master (in `pbs-release/`); not hand-edited
3. **DLR (Dealer)**: Dealer language for hand generation constraints - a DSL for expressing bridge hand requirements
4. **PBN (Portable Bridge Notation)**: Standard bridge hand format, ~160-170KB per file (~500 hands)
5. **BBA (Bridge Base Archive)**: PBN with bidding analysis, ~300-340KB per file
6. **LIN (BBO format)**: Rotated variant for 4-player practice on BBO

### Configuration System

Central configuration in [build-scripts-mac/config.py](build-scripts-mac/config.py):
- SSH host/user for Windows VM
- Drive mappings (P:, S: drives with UNC paths)
- Tool paths (dealer, bba-cli, wkhtmltopdf)
- Default convention cards: `21GF-DEFAULT`, `21GF-GIB`
- Dealer parameters: seed=5, generate=300000000, produce=500
- Pipeline operations order

## Development Practices

### Working with Scenario (.btn) Files

- `.btn` files live in the `btn/` directory and are the single master source. Everything else (`dlr/`, `pbs-release/`, `pbn/`, etc.) is derived — the pipeline does not auto-cascade, so regenerate downstream artifacts explicitly after editing a `.btn`.
- Each `.btn` file defines a bidding scenario with:
  - Dealer language code for hand generation constraints
  - Button metadata for BBO integration (`@chat`, `@convention-card-ns`, `@convention-card-ew`, `@include`, etc.)
  - Optional filtering rules for auction patterns
- The `-PBS.txt` file lists all scenarios and their organization
- When creating new scenarios, follow the existing `.btn` structure
- **Commas in scenario chat**: Use plain regular commas in `.btn` files. The pipeline converts them to wide commas (，) downstream when rendering the `.pbs`; do not hand-type wide commas in `.btn` files.

### Working with the Pipeline

- Operations are composable and can be run independently
- Each operation reads from its input folder and writes to its output folder
- The pipeline can be resumed from any operation using the "+" suffix (e.g., "bba+" runs from bba to end)
- Always test pipeline changes on a single scenario before running on all scenarios
- File-based queueing is used for GUI tools (BBA.exe) that can't run headless

### Working with the VS Code Extension

- The extension auto-activates via `workspaceContains:PBS` or `workspaceContains:-PBS.txt` (see `vs-code/package.json`). Since the `PBS/` folder no longer exists, in practice `-PBS.txt` is the trigger
- Tree views and button grid dynamically update based on file changes
- Commands are registered in [package.json](vs-code/package.json) with menu contributions
- The extension provides context-aware pipeline commands in the editor title bar
- When modifying the extension, use `npm run watch` for continuous compilation

### Cross-Platform Considerations

- Mac is the primary development platform; Windows VM handles Windows-only tools
- SSH runner handles drive mapping and UNC path conversion automatically
- Test Windows tool execution when modifying pipeline operations
- UNC paths must be used for SSH execution (mapped drives don't persist in SSH sessions)

### File Naming Conventions

- `.btn` files use names like `Smolen` or `Weak_2_Bids`
- Generated files maintain the same base name with different extensions
- Scenario names are used as keys throughout the system
- Avoid spaces in scenario names; use underscores instead

## BBO Integration

The system integrates with Bridge Base Online through:

1. **BBOalert Framework**: `-PBS.txt` file contains BBOalert code to import scenarios
2. **JavaScript Automation**: Scripts in `js/` automate BBO table setup and deal import
3. **Button Grid**: Each scenario becomes a clickable button that imports dealer code to BBO
4. **Deal Source**: Dealer code is automatically set in BBO's "Deal source/Advanced" section
5. **Practice Tables**: Scripts can automatically create bidding or teaching tables with proper settings
6. **Deal-source manifest**: `manifest/manifest-{release,beta,test}.json` (built by `py/build_manifest.py` on push) hands consumers the whole menu in one fetch — the button layout plus each scenario's button text, chat, `gib-works`/`bba-works`, and the missing/orphan deltas — replacing the legacy per-`.btn`/`.pbs` scan

Key JavaScript automation functions:
- `setBiddingTable` - Creates and configures a bidding practice table
- `setTeachingTable` - Creates and configures a teaching table
- `setDealerCode` - Imports dealer constraints to BBO
- `displayHCP` - Shows high card points for visible hands

## Key Architecture Decisions

1. **Pipeline as Code**: Operations are Python functions, not configuration files
2. **File-Based Processing**: Each stage produces files consumed by the next stage
3. **Multi-Target Support**: Supports both Mac native dealer and Windows dealer.exe
4. **IDE Integration First**: VS Code extension is the primary UI; CLI is secondary
5. **Modular Operations**: Each pipeline stage is independent and re-runnable
6. **Portable Configuration**: Environment variables instead of hardcoded paths
7. **Cross-Platform Bridge**: SSH and UNC paths enable Mac-Windows workflow

## Project Context

This project is maintained by an 84-year-old bridge enthusiast focused on bridge education without commercial intent. The goal is broad accessibility for bridge players to practice infrequent bidding scenarios. The system bridges multiple tools (dealer, BBA, BBO), operating systems (Mac/Windows), and formats into a cohesive learning platform.
