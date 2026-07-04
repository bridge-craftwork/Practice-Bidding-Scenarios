#!/usr/bin/env python3
"""
Build PBS file from layout configuration.
Reads btn/-layout.txt and generates -PBS-logging-test.txt
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PROJECT_ROOT

# GitHub base URL for PBS files
GITHUB_BASE = "https://github.com/bridge-craftwork/Practice-Bidding-Scenarios/blob/main/pbs-test"


def parse_btn_metadata(btn_path):
    """Parse metadata from BTN file header."""
    metadata = {
        'alias': None,
        'button_text': None,
        'gib_works': True,
        'button_color': None,
        'button_width': None,
    }

    with open(btn_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('#'):
                break

            if line.startswith('# alias:'):
                metadata['alias'] = line.split(':', 1)[1].strip()
            elif line.startswith('# button-text:'):
                metadata['button_text'] = line.split(':', 1)[1].strip()
            elif line.startswith('# gib-works:'):
                metadata['gib_works'] = line.split(':', 1)[1].strip().lower() == 'true'
            elif line.startswith('# button-color:'):
                metadata['button_color'] = line.split(':', 1)[1].strip()
            elif line.startswith('# button-width:'):
                metadata['button_width'] = line.split(':', 1)[1].strip()

    return metadata


def load_all_btn_metadata(btn_dir):
    """Load metadata from all BTN files."""
    metadata = {}
    for filename in os.listdir(btn_dir):
        if filename.endswith('.btn'):
            name = filename[:-4]  # Remove .btn
            btn_path = os.path.join(btn_dir, filename)
            metadata[name] = parse_btn_metadata(btn_path)
    return metadata


def parse_button_item(item, btn_metadata):
    """Parse a button item like 'file', 'file:blue', 'file:38%', or 'file:blue:12%'."""
    item = item.strip()
    parts = item.split(':')
    name = parts[0]
    color = None
    width = None

    # Parse remaining parts - could be color, width, or both
    for part in parts[1:]:
        if part.endswith('%'):
            width = part
        else:
            color = part

    # Get metadata from BTN file
    meta = btn_metadata.get(name, {})

    return {
        'name': name,
        'alias': meta.get('alias', name),
        'button_text': meta.get('button_text', name),
        'gib_works': meta.get('gib_works', True),
        'color': color or meta.get('button_color'),
        'width': width or meta.get('button_width'),
    }


def parse_layout_line(line, btn_metadata):
    """Parse a button row line, handling groups."""
    buttons = []

    # Check for grouped buttons: file1, (file2:blue, file3:blue)
    # Split by comma but respect parentheses
    parts = []
    current = ""
    paren_depth = 0

    for char in line:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        part = part.strip()
        if part.startswith('(') and part.endswith(')'):
            # Grouped buttons - they share 50% width
            group_content = part[1:-1]
            group_items = [s.strip() for s in group_content.split(',')]
            group_buttons = []

            # Calculate width for each button in group
            # They share 50%, distributed evenly (can be adjusted)
            total_width = 50
            n = len(group_items)
            base_width = total_width // n
            remainder = total_width % n

            for i, item in enumerate(group_items):
                btn = parse_button_item(item, btn_metadata)
                # Distribute remainder to last buttons
                btn['width'] = f"{base_width + (1 if i >= n - remainder else 0)}%"
                btn['grouped'] = True
                group_buttons.append(btn)

            buttons.extend(group_buttons)
        else:
            # Single button - 50% width (or 100% if alone)
            btn = parse_button_item(part, btn_metadata)
            btn['grouped'] = False
            buttons.append(btn)

    # If single button not in group, it gets 50% (or 100% if only one)
    non_grouped = [b for b in buttons if not b.get('grouped')]
    grouped = [b for b in buttons if b.get('grouped')]

    if len(non_grouped) == 1 and len(grouped) == 0:
        non_grouped[0]['width'] = '100%'
    elif len(non_grouped) == 2 and len(grouped) == 0:
        for b in non_grouped:
            b['width'] = '50%'
    elif len(non_grouped) == 1 and len(grouped) > 0:
        non_grouped[0]['width'] = '50%'

    return buttons


def generate_pbs(layout_path, btn_metadata, output_path):
    """Generate PBS file from layout."""

    # Collect all scenarios for import declarations
    scenarios = []
    layout_items = []

    with open(layout_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            stripped = line.strip()

            # Skip comments and empty lines (but track empty lines for structure)
            if stripped.startswith('#') or not stripped:
                if not stripped:
                    layout_items.append({'type': 'empty'})
                continue

            if stripped.startswith('[Major]'):
                content = stripped[7:].strip()
                # Support URL: [Major] Title|URL
                if '|' in content:
                    title, url = content.split('|', 1)
                    layout_items.append({'type': 'major', 'title': title.strip(), 'url': url.strip()})
                else:
                    layout_items.append({'type': 'major', 'title': content})
            elif stripped.startswith('[Section]'):
                content = stripped[9:].strip()
                # Support URL: [Section] Title|URL
                if '|' in content:
                    title, url = content.split('|', 1)
                    layout_items.append({'type': 'section', 'title': title.strip(), 'url': url.strip()})
                else:
                    layout_items.append({'type': 'section', 'title': content})
            elif stripped.startswith('[Action]'):
                # Format: [Action] Text|script|width
                content = stripped[8:].strip()
                parts = content.split('|')
                layout_items.append({
                    'type': 'action',
                    'text': parts[0].strip(),
                    'script': parts[1].strip() if len(parts) > 1 else '',
                    'width': parts[2].strip() if len(parts) > 2 else '50',
                })
            elif stripped == '---':
                layout_items.append({'type': 'separator'})
            else:
                # Button row
                buttons = parse_layout_line(stripped, btn_metadata)
                for btn in buttons:
                    # Skip separators
                    if btn['name'] == '---':
                        continue
                    if btn['name'] not in [s['name'] for s in scenarios]:
                        scenarios.append(btn)
                layout_items.append({'type': 'buttons', 'buttons': buttons})

    # Load template
    template_path = os.path.join(os.path.dirname(__file__), 'pbs-template.txt')
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Generate scenario imports
    import_lines = []
    for scenario in scenarios:
        alias = scenario['alias']
        name = scenario['name']
        import_lines.append(f"Import,{alias},{GITHUB_BASE}/{name}.pbs")

    # Generate button section
    button_lines = []
    for item in layout_items:
        if item['type'] == 'empty':
            button_lines.append("")
        elif item['type'] == 'major':
            url = item.get('url', '')
            if url:
                # URL with \n makes it clickable
                button_lines.append(f"Button,{item['title']},{url}\\n,width=100% backgroundColor=LemonChiffon")
            else:
                button_lines.append(f"Button,{item['title']},,width=100% backgroundColor=LemonChiffon")
            button_lines.append("")
        elif item['type'] == 'section':
            url = item.get('url', '')
            if url:
                button_lines.append(f"Button,{item['title']},{url}\\n,width=100% backgroundColor=lightblue")
            else:
                button_lines.append(f"Button,{item['title']},,width=100% backgroundColor=lightblue")
            button_lines.append("")
        elif item['type'] == 'action':
            button_lines.append(f"Button,{item['text']},{item['script']},width={item['width']}% backgroundColor=lightgreen")
        elif item['type'] == 'separator':
            button_lines.append("Button,---")
        elif item['type'] == 'buttons':
            for btn in item['buttons']:
                if btn['name'] == '---':
                    button_lines.append("Button,---")
                else:
                    alias = btn['alias']
                    button_lines.append(f"Import,{alias}")

    # Substitute into template
    output = template.replace('{{SCENARIO_IMPORTS}}', '\n'.join(import_lines))
    output = output.replace('{{BUTTONS}}', '\n'.join(button_lines))

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"Generated: {output_path}")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"  Layout items: {len(layout_items)}")


def update_btn_widths(layout_path, btn_dir, btn_metadata):
    """Update BTN files with calculated widths from layout groupings."""
    width_updates = {}

    with open(layout_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('[') or stripped == '---':
                continue

            buttons = parse_layout_line(stripped, btn_metadata)
            for btn in buttons:
                name = btn['name']
                width = btn.get('width')
                color = btn.get('color')
                if width or color:
                    width_updates[name] = {'width': width, 'color': color}

    # Update BTN files
    updated = 0
    for name, updates in width_updates.items():
        btn_path = os.path.join(btn_dir, f"{name}.btn")
        if not os.path.exists(btn_path):
            continue

        with open(btn_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content

        # Update width
        if updates['width']:
            if '# button-width:' in new_content:
                new_content = re.sub(
                    r'^# button-width:.*$',
                    f"# button-width: {updates['width']}",
                    new_content,
                    flags=re.MULTILINE
                )
            else:
                # Add after last metadata line
                lines = new_content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('#'):
                        lines.insert(i, f"# button-width: {updates['width']}")
                        break
                new_content = '\n'.join(lines)

        # Update color
        if updates['color']:
            if '# button-color:' in new_content:
                new_content = re.sub(
                    r'^# button-color:.*$',
                    f"# button-color: {updates['color']}",
                    new_content,
                    flags=re.MULTILINE
                )
            else:
                lines = new_content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('#'):
                        lines.insert(i, f"# button-color: {updates['color']}")
                        break
                new_content = '\n'.join(lines)

        if new_content != content:
            with open(btn_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1

    return updated


def main():
    layout_path = os.path.join(PROJECT_ROOT, "btn", "-layout.txt")
    btn_dir = os.path.join(PROJECT_ROOT, "btn")
    output_path = os.path.join(PROJECT_ROOT, "-PBS-logging-test.txt")

    # Load BTN metadata
    print("Loading BTN metadata...")
    btn_metadata = load_all_btn_metadata(btn_dir)
    print(f"  Loaded {len(btn_metadata)} BTN files")

    # Note: Button widths and colors are NOT stored in BTN files.
    # They are derived from the layout file at PBS generation time.
    # This allows changing layouts without regenerating BTN files.

    # Generate PBS
    print("Generating PBS...")
    generate_pbs(layout_path, btn_metadata, output_path)


if __name__ == "__main__":
    main()
