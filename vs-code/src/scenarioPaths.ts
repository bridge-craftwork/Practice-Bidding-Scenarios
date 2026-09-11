import * as path from 'path';

/**
 * Folders whose files are named after a scenario: the btn/ master source plus
 * the pipeline's per-scenario outputs. A file directly inside one of these
 * belongs to the scenario its name (minus extension) spells.
 */
export const ARTIFACT_DIRS = [
    'btn',
    'dlr',
    'pbn',
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
