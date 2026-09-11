# PBS Dynamic Layout System

**Version:** 2.0
**File:** `runtime/pbsDynamicLayout.js` in pbs-bbo-extension

## Overview

The PBS Dynamic Layout System is a BBOalert plugin that dynamically generates Practice Bidding Scenarios buttons at runtime. Instead of using a static, pre-built button list, it fetches the menu manifest from GitHub each time the plugin loads, and fetches a scenario's `.dlr` file when its button is clicked.

The plugin itself lives in the pbs-bbo-extension repo. This repo supplies what it reads: the layout files, `dlr/`, and `manifest/` (see [manifest/README.md](manifest/README.md)).

## Features

- **Dynamic Button Generation**: Buttons are created at runtime based on layout configuration files
- **One-Fetch Menu**: Layout, button text and chat come from a single manifest file
- **Missing File Detection**: Buttons whose `.dlr` file is missing are displayed with red text
- **Test Mode**: Optional diagnostic features for development
- **Instant Config Reload**: Changing settings immediately rebuilds the button list
- **Expand/Collapse**: Section headers collapse/expand their contents; master header toggles all

## Configuration

Access plugin settings via BBOalert's config menu (select "PBS Dynamic Layout"):

| Setting | Description |
|---------|-------------|
| **Enable_Test_Mode** | Shows the diagnostic sections (missing and orphan scenarios) |
| **Use_Beta_Layout** | Switches from release layout to beta layout file |

Settings take effect immediately - no page refresh required.

## File Structure

```
Practice-Bidding-Scenarios/
├── btn/
│   ├── -button-layout-release.txt   # Production layout
│   └── -button-layout-beta.txt      # Beta/testing layout
├── dlr/                              # Dealer scripts, one per scenario
│   ├── Stayman.dlr
│   ├── Minor_Suit_Opener.dlr
│   └── ...
└── manifest/
    ├── manifest-release.json         # Menu built from the release layout
    └── manifest-beta.json            # Menu built from the beta layout
```

## Layout File Format

Layout files define the button structure using a simple text format:

```
# Comment line

[Major] Title                           # Yellow header (LemonChiffon)
[Major] Title|URL                       # Yellow header with link

[Section] Title                         # Blue collapsible header (lightblue)

[Action] Text|%scriptName%|width        # Green action button (lightgreen)

filename1,            filename2         # Two buttons at 50% each
filename:blue                           # Button with blue text
filename:blue:38%                       # Button with blue text, 38% width
---                                     # Separator/placeholder

(btn1:blue, btn2:blue, btn3:blue)       # Grouped buttons share 50% width
filename1, (btn2:blue, btn3:blue)       # 50% + grouped 50%
```

### Layout Elements

| Element | Format | Description |
|---------|--------|-------------|
| Major Header | `[Major] Title` | Yellow (LemonChiffon) full-width header. First one is master expand/collapse. |
| Section Header | `[Section] Title` | Blue (lightblue) collapsible section header |
| Action Button | `[Action] Text\|script\|width` | Green (lightgreen) button that runs a script |
| Button Row | `name1, name2` | Row of scenario buttons (default 50% each) |
| Separator | `---` | Placeholder/divider button |
| Grouped | `(a, b, c)` | Multiple buttons sharing one 50% slot |

### Button Modifiers

- `:blue` - Sets text color to blue
- `:38%` - Sets explicit width percentage
- Combine: `filename:blue:12%`

## DLR File Format

Each `dlr/<name>.dlr` starts with a header, then the dealer code:

```
# button-text: Button Text
# alias: AliasName
# convention-card-ns: 21GF-DEFAULT
dealer north
/*@chat
chat message
@chat*/
... dealer code here ...
```

On a click the plugin drops the header, the `dealer` line and the chat block, and passes the rest to `setDealerCode(code, seat, true)`. The manifest carries the button text and chat, taken from the same header.

A push to `main` publishes a changed `.dlr` (the pipeline's `release` operation does it). Which buttons each channel shows is set by the two layout files.

## Test Mode Features

When **Enable_Test_Mode** is checked:

### 1. MISSING PBS FILES Section
Lists buttons referenced in the layout file that don't have a corresponding `.dlr` file in `dlr/`. Displayed with:
- Light salmon (lightsalmon) header
- Red text on missing buttons

### 2. ORPHAN SCENARIOS Section
Lists `.dlr` files that aren't referenced by any button in the layout. This is where a new scenario shows up before it has a button. Displayed with:
- Plum colored header
- Purple text on orphan buttons
- Buttons are still clickable to test the scenarios

## How It Works

### Initialization Flow

1. Load saved config from localStorage
2. Fetch the manifest (release or beta based on setting)
3. Create buttons from the manifest's layout, in order
4. If test mode: insert the diagnostic sections
5. Set up expand/collapse handlers
6. Collapse all sections initially
7. On a click, fetch that scenario's `.dlr` and load it

### Config Change Detection

The plugin uses an `onAnyMutation` handler to detect when config changes:

1. Compares current localStorage config to last known state
2. If changed, clears all dynamic buttons
3. Re-fetches the manifest
4. Rebuilds all buttons with new settings

## GitHub URLs

| Resource | URL Pattern |
|----------|-------------|
| Menu (release) | `raw.githubusercontent.com/.../manifest/manifest-release.json` |
| Menu (beta) | `raw.githubusercontent.com/.../manifest/manifest-beta.json` |
| Dealer scripts | `raw.githubusercontent.com/.../dlr/{name}.dlr` |

## Expand/Collapse Behavior

- **Yellow header** (first `[Major]`): Master toggle - expands/collapses ALL scenario buttons
- **Blue headers** (`[Section]`): Toggle buttons within that section only
- **Initial state**: All sections start collapsed

## Troubleshooting

### Buttons not appearing
- Check browser console for "PBS Dynamic" log messages
- Verify GitHub raw URLs are accessible
- Check for JavaScript errors

### Missing file shown in red
- The layout references a scenario that has no file in `dlr/`
- Either run the `dlr` operation and push the `.dlr`, or remove the button from the layout

### Config changes not taking effect
- Ensure you click OK in the config dialog (not just close it)
- Check console for "Config changed, triggering rebuild" message

### Buttons in wrong order
- Buttons are created in the order of the manifest's layout
- Check the layout file, then check that the manifest has been rebuilt since it changed

## Version History

- **v2.0**: Added immediate rebuild on config change
- **v1.9**: Added missing/orphan diagnostics, beta layout toggle
- **v1.8**: Added expand/collapse, start collapsed
- **v1.7**: Reordered test buttons after action buttons
- **v1.0**: Initial dynamic layout system
