import * as fs from 'fs';

export interface PbsButton {
    label: string;
    description: string;
    scriptId: string;
    backgroundColor?: string;
    width?: string;
    filePath?: string;
    lineNumber?: number;
    targetFilename?: string;
}

export interface PbsSection {
    title: string;
    buttons: PbsButton[];
    backgroundColor?: string;
}

/**
 * Parse a single BBOalert Button line (may span multiple lines with \n\
 * continuation), as found in the legacy -PBS.txt main config.
 * Format: Button,<label>,<description with \n\>,<styling>
 */
function parseButtonLine(buttonContent: string, filePath?: string, lineNumber?: number): PbsButton | null {
    // Remove the "Button," prefix
    if (!buttonContent.startsWith('Button,')) {
        return null;
    }

    const content = buttonContent.substring(7);

    // Join multi-line content (remove \n\ continuations)
    const normalizedContent = content.replace(/\\n\\\s*\n/g, '\\n');

    // Split by comma, but be careful with commas in the description
    // Format: label,description,styling
    const firstCommaIndex = normalizedContent.indexOf(',');
    if (firstCommaIndex === -1) {
        // Just a label, no description (section header or separator)
        const label = normalizedContent.trim();
        if (label === '') {
            return null; // Empty, skip
        }
        // Return the button (including '---' placeholders)
        return {
            label: label,
            description: '',
            scriptId: '',
            filePath,
            lineNumber
        };
    }

    const label = normalizedContent.substring(0, firstCommaIndex).trim();
    const rest = normalizedContent.substring(firstCommaIndex + 1);

    // Extract the script ID (looks like %ScriptName%)
    const scriptIdMatch = rest.match(/%([^%]+)%/);
    const scriptId = scriptIdMatch ? scriptIdMatch[1] : '';

    // Extract styling (after the last % or after the script ID)
    let styling = '';
    let description = rest;

    if (scriptIdMatch) {
        const afterScriptId = rest.substring(rest.lastIndexOf('%' + scriptIdMatch[1] + '%') + scriptIdMatch[0].length);
        if (afterScriptId.startsWith(',')) {
            styling = afterScriptId.substring(1).trim();
        }
        // Description is everything before the script ID
        description = rest.substring(0, rest.indexOf('%' + scriptIdMatch[1] + '%'));
    } else {
        // No script ID - check if rest contains styling (e.g., ",width=100% backgroundColor=lightblue")
        // Format could be: ,styling or description,styling
        const lastCommaIndex = rest.lastIndexOf(',');
        if (lastCommaIndex !== -1) {
            const possibleStyling = rest.substring(lastCommaIndex + 1).trim();
            // Check if it looks like styling (contains = sign)
            if (possibleStyling.includes('=')) {
                styling = possibleStyling;
                description = rest.substring(0, lastCommaIndex);
            }
        }
    }

    // Clean up description - replace \n with actual newlines for display
    description = description
        .replace(/\\n/g, '\n')
        .replace(/,\s*$/, '')
        .trim();

    // Parse styling from the full rest string as fallback (for section headers like ",,width=100% backgroundColor=lightblue")
    const bgMatch = styling.match(/backgroundColor=(\w+)/) || rest.match(/backgroundColor=(\w+)/);
    const widthMatch = styling.match(/width=(\d+%?)/) || rest.match(/width=(\d+%?)/);

    return {
        label,
        description,
        scriptId,
        backgroundColor: bgMatch ? bgMatch[1] : undefined,
        width: widthMatch ? widthMatch[1] : undefined,
        filePath,
        lineNumber
    };
}

/**
 * Parse the button layout file (btn/-button-layout-release.txt) to understand the panel structure.
 * Format:
 *   [Major] Title           - Major header (LemonChiffon background)
 *   [Section] Title         - Section header (lightblue, collapsible)
 *   [Action] Text|script|width - Action button (lightgreen)
 *   ---                     - Separator row
 *   file1, file2            - Button row (2 buttons at 50% each)
 *   # comment               - Comment line
 */
export function parseButtonLayoutFile(layoutPath: string): PbsSection[] {
    const sections: PbsSection[] = [];

    if (!fs.existsSync(layoutPath)) {
        return sections;
    }

    const content = fs.readFileSync(layoutPath, 'utf-8');
    const lines = content.split('\n');

    let currentSection: PbsSection | null = null;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Skip comments and empty lines
        if (line.startsWith('#') || line === '') {
            continue;
        }

        // Major header: [Major] Title
        if (line.startsWith('[Major]')) {
            if (currentSection) {
                sections.push(currentSection);
            }
            const title = line.substring(7).trim();
            currentSection = {
                title: title,
                buttons: [],
                backgroundColor: 'LemonChiffon'
            };
            continue;
        }

        // Section header: [Section] Title
        if (line.startsWith('[Section]')) {
            if (currentSection) {
                sections.push(currentSection);
            }
            const title = line.substring(9).trim();
            currentSection = {
                title: title,
                buttons: [],
                backgroundColor: 'lightblue'
            };
            continue;
        }

        // Action button: [Action] Text|script|width - skip these for tree view
        if (line.startsWith('[Action]')) {
            continue;
        }

        // Separator: ---
        if (line === '---') {
            continue;
        }

        // Button row: file1, file2 or file1, (file2:blue, file3:blue)
        if (currentSection) {
            // Parse button names from the row
            const buttonNames = parseLayoutRow(line);
            for (const name of buttonNames) {
                currentSection.buttons.push({
                    label: name.replace(/_/g, ' '),
                    description: '',
                    scriptId: name,
                    filePath: '',  // Will be resolved later
                    lineNumber: i + 1
                });
            }
        }
    }

    if (currentSection) {
        sections.push(currentSection);
    }

    return sections;
}

/**
 * Parse a layout row to extract button names.
 * Handles: file1, file2 and file1, (file2:blue, file3:blue)
 */
function parseLayoutRow(line: string): string[] {
    const names: string[] = [];

    // Split by comma but respect parentheses
    const parts: string[] = [];
    let current = '';
    let parenDepth = 0;

    for (const char of line) {
        if (char === '(') {
            parenDepth++;
            current += char;
        } else if (char === ')') {
            parenDepth--;
            current += char;
        } else if (char === ',' && parenDepth === 0) {
            parts.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    if (current.trim()) {
        parts.push(current.trim());
    }

    for (const part of parts) {
        let cleaned = part.trim();

        // Skip separators
        if (cleaned === '---') {
            continue;
        }

        // Handle grouped buttons: (file1:blue, file2:blue)
        if (cleaned.startsWith('(') && cleaned.endsWith(')')) {
            const groupContent = cleaned.slice(1, -1);
            const groupItems = groupContent.split(',').map(s => s.trim());
            for (const item of groupItems) {
                // Remove color/width suffixes: file:blue:12% -> file
                const name = item.split(':')[0].trim();
                if (name && name !== '---') {
                    names.push(name);
                }
            }
        } else {
            // Regular button: file or file:blue:12%
            const name = cleaned.split(':')[0].trim();
            if (name && name !== '---') {
                names.push(name);
            }
        }
    }

    return names;
}

/**
 * Parse the main PBS configuration file (-PBS.txt) to understand the panel structure
 * @deprecated Use parseButtonLayoutFile instead for the new layout format
 */
export function parseMainPbsConfig(configPath: string): PbsSection[] {
    const sections: PbsSection[] = [];

    if (!fs.existsSync(configPath)) {
        return sections;
    }

    const content = fs.readFileSync(configPath, 'utf-8');
    const lines = content.split('\n');

    // First pass: collect import declarations with URLs (scriptId -> targetFilename mapping)
    const importDeclarations = new Map<string, string>();
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith('Import,')) {
            const parts = trimmedLine.split(',');
            if (parts.length >= 3) {
                const scriptId = parts[1].trim();
                const url = parts[2].trim();
                // Extract filename from URL like .../PBS/GIB_1N
                const urlMatch = url.match(/\/PBS\/([^/]+)$/);
                if (urlMatch) {
                    importDeclarations.set(scriptId, urlMatch[1]);
                }
            }
        }
    }

    let currentSection: PbsSection | null = null;

    // Second pass: process sections and buttons
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Skip comments and empty lines
        if (line.startsWith('//') || line.startsWith('#') || line === '') {
            continue;
        }

        // Section header button (has backgroundColor=lightblue or LemonChiffon)
        if (line.startsWith('Button,')) {
            const button = parseButtonLine(line, configPath, i + 1);
            if (button) {
                // Check if it's a section header (lightblue or LemonChiffon background)
                if (button.backgroundColor === 'lightblue' || button.backgroundColor === 'LemonChiffon') {
                    if (currentSection) {
                        sections.push(currentSection);
                    }
                    currentSection = {
                        title: button.label,
                        buttons: [],
                        backgroundColor: button.backgroundColor
                    };
                } else if (button.label === '---') {
                    // Placeholder button - add it to the current section
                    if (currentSection) {
                        currentSection.buttons.push(button);
                    }
                } else if (currentSection) {
                    // Regular button in current section
                    currentSection.buttons.push(button);
                }
            }
        }

        // Import statement - this references a PBS file
        if (line.startsWith('Import,')) {
            const parts = line.split(',');
            if (parts.length >= 2 && currentSection) {
                const scriptId = parts[1].trim();
                // Look up target filename from declarations, or extract from URL if present
                let targetFilename = importDeclarations.get(scriptId) || '';
                if (!targetFilename && parts.length >= 3) {
                    const url = parts[2].trim();
                    const urlMatch = url.match(/\/PBS\/([^/]+)$/);
                    if (urlMatch) {
                        targetFilename = urlMatch[1];
                    }
                }
                // Create a placeholder button for the import
                currentSection.buttons.push({
                    label: scriptId,
                    description: '',
                    scriptId: scriptId,
                    targetFilename: targetFilename, // Store target filename for matching
                    filePath: '', // Will be resolved later
                    lineNumber: i + 1
                });
            }
        }
    }

    if (currentSection) {
        sections.push(currentSection);
    }

    return sections;
}
