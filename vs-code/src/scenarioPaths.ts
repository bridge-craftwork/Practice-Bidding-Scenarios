import * as fs from 'fs';
import * as path from 'path';

/**
 * Folders whose files are named after a scenario: the btn/ master source plus
 * the pipeline's per-scenario outputs. A file directly inside one of these
 * belongs to the scenario its name (minus extension) spells.
 */
export const ARTIFACT_DIRS = [
    'btn',
    'dlr',
    'dlr-leveled',
    'pbn',
    'pbn-leveled',
    'pbn-rotated-for-4-players',
    'bba',
    'bba-filtered',
    'bba-filtered-out',
    'bba-summary',
    'bidding-sheets',
    'lin',
    'lin-rotated-for-4-players',
    'quiz'
];

/**
 * Get the scenario name from a file path in any of the ARTIFACT_DIRS,
 * or undefined if the file isn't a scenario file.
 */
export function getScenarioFromPath(filePath: string | undefined): string | undefined {
    if (!filePath) {
        return undefined;
    }

    const dirName = path.basename(path.dirname(filePath));
    if (!ARTIFACT_DIRS.includes(dirName)) {
        return undefined;
    }

    const baseName = path.basename(filePath).replace(/\.(btn|pbn|dlr|pdf|html|txt|lin|json)$/i, '');

    // Bidding sheet names like "1N Bidding Sheets.pdf" -> "1N"
    const biddingSheetMatch = baseName.match(/^(.+?)\s+Bidding Sheets?$/i);
    if (biddingSheetMatch) {
        return biddingSheetMatch[1];
    }

    return baseName;
}

// dealer3 reads the HandType_ prefix in any case
const HAND_TYPE_RE = /^\s*handtype_\w+\s*=/im;

/**
 * True if the scenario is leveled (issue #322): it has a dlr-leveled/ copy, or
 * its dlr declares hand types, so the level operation will write one.
 */
export function isLeveled(scenario: string, root: string): boolean {
    if (fs.existsSync(path.join(root, 'dlr-leveled', `${scenario}.dlr`))) {
        return true;
    }
    try {
        return HAND_TYPE_RE.test(fs.readFileSync(path.join(root, 'dlr', `${scenario}.dlr`), 'utf8'));
    } catch {
        return false;
    }
}

/**
 * The PBN that rotate and bba read, by the pipeline's rule
 * (build-scripts-mac/utils/leveling.py): pbn-leveled/ when leveled.
 */
export function pbnFor(scenario: string, root: string): string {
    return fs.existsSync(path.join(root, 'dlr-leveled', `${scenario}.dlr`))
        ? path.join(root, 'pbn-leveled', `${scenario}.pbn`)
        : path.join(root, 'pbn', `${scenario}.pbn`);
}
