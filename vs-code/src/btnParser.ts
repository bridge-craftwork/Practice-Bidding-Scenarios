import * as fs from 'fs';
import * as path from 'path';
import { PbsButton, PbsSection } from './pbsParser';

export interface BtnMetadata {
    bbaWorks: boolean;
    gibWorks: boolean;
    auctionFilter: string | undefined;
}

// Cache to avoid repeated file reads
const metadataCache = new Map<string, BtnMetadata>();

/**
 * Get metadata from a BTN file for a scenario.
 * Results are cached for performance.
 *
 * @param scenario Scenario name (e.g., "Smolen")
 * @param workspaceRoot Workspace root path
 * @returns Metadata object with bbaWorks, gibWorks, and auctionFilter
 */
export function getBtnMetadata(scenario: string, workspaceRoot: string): BtnMetadata {
    const cacheKey = `${workspaceRoot}:${scenario}`;

    if (metadataCache.has(cacheKey)) {
        return metadataCache.get(cacheKey)!;
    }

    const btnPath = path.join(workspaceRoot, 'btn', `${scenario}.btn`);
    const metadata: BtnMetadata = {
        bbaWorks: false,  // Default to false if not specified
        gibWorks: false,  // Default to false if not specified
        auctionFilter: undefined
    };

    if (!fs.existsSync(btnPath)) {
        return metadata;
    }

    try {
        const content = fs.readFileSync(btnPath, 'utf-8');
        const lines = content.split('\n').slice(0, 20); // Only check first 20 lines

        for (const line of lines) {
            const bbaMatch = line.match(/^#\s*bba-works:\s*(.+)$/i);
            if (bbaMatch) {
                metadata.bbaWorks = bbaMatch[1].trim().toLowerCase() === 'true';
            }

            const gibMatch = line.match(/^#\s*gib-works:\s*(.+)$/i);
            if (gibMatch) {
                metadata.gibWorks = gibMatch[1].trim().toLowerCase() === 'true';
            }

            const filterMatch = line.match(/^#\s*auction-filter:\s*(.+)$/i);
            if (filterMatch) {
                metadata.auctionFilter = filterMatch[1].trim();
            }
        }
    } catch {
        // Return defaults on error
    }

    metadataCache.set(cacheKey, metadata);
    return metadata;
}

/**
 * Clear the metadata cache.
 * Should be called when BTN files change.
 */
export function clearMetadataCache(): void {
    metadataCache.clear();
}

/**
 * Build the scenario button for one .btn file from its header:
 *   # alias: <script id>        (defaults to the file name)
 *   # button-text: <label>      (defaults to the alias)
 *   # gib-works: false          -> lightpink background, as BBO shows it
 *   /*@chat ... @chat*\/         -> tooltip / description
 */
export function parseBtnButton(filePath: string): PbsButton | null {
    let content: string;
    try {
        content = fs.readFileSync(filePath, 'utf-8');
    } catch {
        return null;
    }

    const name = path.basename(filePath, '.btn');
    let alias: string | undefined;
    let buttonText: string | undefined;
    let gibWorks = true;  // Matches the pipeline: only an explicit "false" turns the button pink
    const chatLines: string[] = [];
    let inChat = false;
    let chatDone = false;

    for (const line of content.split('\n')) {
        const stripped = line.trim();
        if (inChat) {
            if (stripped.endsWith('@chat*/')) {
                inChat = false;
                chatDone = true;
            } else {
                chatLines.push(line.replace(/\r$/, ''));
            }
            continue;
        }
        if (!chatDone && stripped.startsWith('/*@chat')) {
            inChat = true;
            continue;
        }

        const meta = stripped.match(/^#\s*(alias|button-text|gib-works):\s*(.*)$/i);
        if (meta) {
            const key = meta[1].toLowerCase();
            const value = meta[2].trim();
            if (key === 'alias' && alias === undefined) {
                alias = value;
            } else if (key === 'button-text' && buttonText === undefined) {
                buttonText = value;
            } else if (key === 'gib-works') {
                gibWorks = value.toLowerCase() !== 'false';
            }
        }
    }

    const scriptId = alias || name;
    return {
        label: buttonText || scriptId,
        description: chatLines.join('\n').replace(/^\n+|\n+$/g, ''),
        scriptId,
        backgroundColor: gibWorks ? undefined : 'lightpink',
        filePath,
        lineNumber: 1
    };
}

/**
 * Replace the placeholder buttons a layout file produces (scriptId = the name
 * written in the layout, no filePath) with the real .btn buttons.
 * Layout names are .btn file names; aliases, the legacy -PBS.txt Import
 * target, and a loose name match are tried in turn as fallbacks.
 *
 * @returns the file paths of every button placed in a section
 */
export function resolveLayoutSections(sections: PbsSection[], buttons: PbsButton[]): Set<string> {
    const byName = new Map<string, PbsButton>();
    const byAlias = new Map<string, PbsButton>();
    for (const button of buttons) {
        if (button.filePath) {
            byName.set(path.basename(button.filePath, '.btn'), button);
        }
        if (button.scriptId) {
            byAlias.set(button.scriptId, button);
        }
    }

    const mappedFilePaths = new Set<string>();

    for (const section of sections) {
        for (let i = 0; i < section.buttons.length; i++) {
            const button = section.buttons[i];
            if (button.filePath) {
                mappedFilePaths.add(button.filePath);
                continue;
            }
            if (!button.scriptId) {
                continue;
            }

            let resolved = byName.get(button.scriptId)
                ?? byAlias.get(button.scriptId)
                ?? (button.targetFilename ? byName.get(button.targetFilename) : undefined);

            if (!resolved) {
                // Loose match: ignore case, underscores and dashes; prefer an exact
                // match, else the shortest name that contains the layout name
                const wanted = button.scriptId.toLowerCase().replace(/[_-]/g, '');
                let bestScore = 0;
                for (const [name, candidate] of byName) {
                    const normalized = name.toLowerCase().replace(/[_-]/g, '');
                    if (normalized === wanted) {
                        resolved = candidate;
                        break;
                    }
                    if (normalized.includes(wanted)) {
                        const score = wanted.length / normalized.length;
                        if (score > bestScore) {
                            bestScore = score;
                            resolved = candidate;
                        }
                    }
                }
            }

            if (resolved) {
                section.buttons[i] = resolved;
                if (resolved.filePath) {
                    mappedFilePaths.add(resolved.filePath);
                }
            }
        }
    }

    return mappedFilePaths;
}

/**
 * Build scenario buttons for every btn/*.btn file (layout files like
 * -button-layout-release.txt are skipped).
 */
export function parseBtnDirectory(btnDir: string): PbsButton[] {
    if (!fs.existsSync(btnDir)) {
        return [];
    }

    const buttons: PbsButton[] = [];
    for (const file of fs.readdirSync(btnDir)) {
        if (!file.endsWith('.btn')) {
            continue;
        }
        const button = parseBtnButton(path.join(btnDir, file));
        if (button) {
            buttons.push(button);
        }
    }
    return buttons;
}
