import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getBtnMetadata, clearMetadataCache } from './btnParser';
import { getScenarioFromPath, isLeveled, pbnFor } from './scenarioPaths';

/**
 * Find the first packaged PBN file for a scenario in the Bidding Scenarios hierarchy.
 * Scans Bidding Scenarios/{section}/{scenario}/ for {scenario}.pbn.
 * Returns the path (which may not exist yet if package hasn't been run).
 */
function findPackagePath(scenario: string, root: string): string {
    const bsDir = path.join(root, 'Bidding Scenarios');
    if (fs.existsSync(bsDir)) {
        try {
            const sections = fs.readdirSync(bsDir).sort();
            for (const section of sections) {
                const scenarioDir = path.join(bsDir, section, scenario);
                if (fs.existsSync(scenarioDir)) {
                    return path.join(scenarioDir, `${scenario}.pbn`);
                }
            }
        } catch { /* ignore read errors */ }
    }
    // Not yet packaged — return a path in a placeholder location
    return path.join(bsDir, '_', scenario, `${scenario}.pbn`);
}

// Define all artifacts in pipeline order with their dependencies
// requiresBba indicates artifacts that need bba-works=true to be shown
// requiresLeveled indicates artifacts only a leveled scenario has (issue #322)
const ARTIFACTS = [
    {
        name: 'dlr',
        shortName: 'dlr',
        requiresBba: false,
        requiresLeveled: false,
        getPath: (s: string, r: string) => path.join(r, 'dlr', `${s}.dlr`),
        getSourcePath: (s: string, r: string) => path.join(r, 'btn', `${s}.btn`),
        command: 'pbs.runDlr'
    },
    {
        name: 'dlr-leveled',
        shortName: 'lvl',
        requiresBba: false,
        requiresLeveled: true,
        getPath: (s: string, r: string) => path.join(r, 'dlr-leveled', `${s}.dlr`),
        getSourcePath: (s: string, r: string) => path.join(r, 'dlr', `${s}.dlr`),
        command: 'pbs.runLevel'
    },
    {
        name: 'pbn',
        shortName: 'pbn',
        requiresBba: false,
        requiresLeveled: false,
        getPath: (s: string, r: string) => path.join(r, 'pbn', `${s}.pbn`),
        getSourcePath: (s: string, r: string) => path.join(r, 'dlr', `${s}.dlr`),
        command: 'pbs.runPbn'
    },
    {
        name: 'pbn-leveled',
        shortName: 'pbnL',
        requiresBba: false,
        requiresLeveled: true,
        getPath: (s: string, r: string) => path.join(r, 'pbn-leveled', `${s}.pbn`),
        getSourcePath: (s: string, r: string) => path.join(r, 'dlr-leveled', `${s}.dlr`),
        command: 'pbs.runPbn'
    },
    {
        // Solving writes into the deal file rather than a file of its own, so
        // there is no artifact whose mtime could answer "is this solved?".
        // The file's `% solved: n/m deals` stamp answers it instead, which is
        // why this row reads a header rather than comparing timestamps.
        name: 'solve',
        shortName: 'dd',
        requiresBba: false,
        requiresLeveled: false,
        getPath: (s: string, r: string) => pbnFor(s, r),
        getSourcePath: (s: string, r: string) => pbnFor(s, r),
        command: 'pbs.runSolve',
        fromStamp: true
    },
    {
        name: 'rotate',
        shortName: 'rot',
        requiresBba: false,
        requiresLeveled: false,
        getPath: (s: string, r: string) => path.join(r, 'pbn-rotated-for-4-players', `${s}.pbn`),
        getSourcePath: (s: string, r: string) => pbnFor(s, r),
        command: 'pbs.runRotate'
    },
    {
        name: 'bba',
        shortName: 'bba',
        requiresBba: true,
        requiresLeveled: false,
        getPath: (s: string, r: string) => path.join(r, 'bba', `${s}.pbn`),
        getSourcePath: (s: string, r: string) => pbnFor(s, r),
        command: 'pbs.runBba'
    },
    {
        name: 'filter',
        shortName: 'flt',
        requiresBba: true,
        getPath: (s: string, r: string) => path.join(r, 'bba-filtered', `${s}.pbn`),
        getSourcePath: (s: string, r: string) => path.join(r, 'bba', `${s}.pbn`),
        command: 'pbs.runFilter'
    },
    {
        name: 'sheet',
        shortName: 'sheet',
        requiresBba: true,
        getPath: (s: string, r: string) => path.join(r, 'bidding-sheets', `${s} Bidding Sheets.pdf`),
        getSourcePath: (s: string, r: string) => path.join(r, 'bba-filtered', `${s}.pbn`),
        command: 'pbs.runBiddingSheet'
    },
    {
        name: 'quiz',
        shortName: 'quiz',
        requiresBba: true,
        getPath: (s: string, r: string) => path.join(r, 'quiz', `${s}.pdf`),
        getSourcePath: (s: string, r: string) => path.join(r, 'bba-filtered', `${s}.pbn`),
        command: 'pbs.runQuiz'
    },
    {
        name: 'package',
        shortName: 'pkg',
        requiresBba: false,
        getPath: (s: string, r: string) => findPackagePath(s, r),
        getSourcePath: (s: string, r: string) => {
            // Package copies from bba-filtered (with pbn fallback), so compare against actual source
            const filtered = path.join(r, 'bba-filtered', `${s}.pbn`);
            if (fs.existsSync(filtered)) { return filtered; }
            return pbnFor(s, r);
        },
        command: 'pbs.runPackage'
    }
];

type ArtifactStatus = 'fresh' | 'stale' | 'missing' | 'unchecked';

// Tolerance for timestamp comparison (ms). Git checkout/commit resets file
// timestamps to the same second with random sub-second ordering, which can
// make a downstream artifact appear older than its source even though both
// were written in the same pipeline run.
const FRESHNESS_TOLERANCE_MS = 1000;

/**
 * What a deal file's `% solved: n/m deals` stamp says, or null if it has none.
 *
 * Only the header is read: the stamp is in the first few lines, and the
 * alternative -- counting double-dummy tags through a quarter of a megabyte --
 * would be paid on every refresh of this panel.
 */
function readSolvedStamp(pbnPath: string): { deals: number, solved: number } | null {
    let head = '';
    try {
        const fd = fs.openSync(pbnPath, 'r');
        try {
            const buf = Buffer.alloc(4096);
            const read = fs.readSync(fd, buf, 0, buf.length, 0);
            head = buf.toString('utf8', 0, read);
        } finally {
            fs.closeSync(fd);
        }
    } catch {
        return null;
    }

    const m = head.match(/^% solved: (\d+)\/(\d+) deals/m);
    if (!m) { return null; }
    return { solved: parseInt(m[1], 10), deals: parseInt(m[2], 10) };
}

interface ArtifactInfo {
    name: string;
    shortName: string;
    status: ArtifactStatus;
    command: string;
    artifactPath: string;
    /** For a stamped artifact: what its stamp claims, for the tooltip. */
    detail?: string;
}

/**
 * Tree item for the current scenario view
 */
export class ScenarioTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly isRoot: boolean = false,
        public readonly artifactInfo?: ArtifactInfo
    ) {
        super(label, collapsibleState);

        if (isRoot) {
            this.iconPath = new vscode.ThemeIcon('file-code');
            this.contextValue = 'scenario';
        } else if (artifactInfo) {
            // Set icon based on status
            switch (artifactInfo.status) {
                case 'fresh':
                    this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'));
                    break;
                case 'stale':
                    this.iconPath = new vscode.ThemeIcon('sync', new vscode.ThemeColor('testing.iconQueued'));
                    break;
                case 'missing':
                    this.iconPath = new vscode.ThemeIcon('close', new vscode.ThemeColor('testing.iconFailed'));
                    break;
                case 'unchecked':
                    // Freshness checks muted — grey check: "not flagged", but NOT a
                    // verified-fresh (green) claim
                    this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('descriptionForeground'));
                    break;
            }

            // Set command to open the artifact file (if it exists)
            if (artifactInfo.status !== 'missing') {
                this.command = {
                    command: 'pbs.openPbsFile',
                    title: `Open ${artifactInfo.name}`,
                    arguments: [artifactInfo.artifactPath]
                };
            }

            // Tooltip with path and status
            let statusText = artifactInfo.status === 'fresh' ? 'Up to date' :
                artifactInfo.status === 'stale' ? 'Needs rebuild' :
                artifactInfo.status === 'unchecked' ? 'Stale warning muted' : 'Not yet built';
            // A stamped artifact says how much of itself is done, which is more
            // use than "up to date" on its own.
            if (artifactInfo.detail) {
                statusText = `${statusText} — ${artifactInfo.detail}`;
            }
            const clickAction = artifactInfo.status === 'missing' ? '' : '\n\n*Click to open*';
            this.tooltip = new vscode.MarkdownString(`**${artifactInfo.name}**\n\n${statusText}\n\n\`${artifactInfo.artifactPath}\`${clickAction}`);
            this.contextValue = 'artifact';
            this.resourceUri = vscode.Uri.file(artifactInfo.artifactPath);
        }
    }
}

/**
 * Provider for the current scenario tree view
 */
export class CurrentScenarioProvider implements vscode.TreeDataProvider<ScenarioTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ScenarioTreeItem | undefined | null | void> = new vscode.EventEmitter<ScenarioTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<ScenarioTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private currentScenario: string | undefined;
    private disposables: vscode.Disposable[] = [];
    // Per-scenario, session-scoped mute set for the panel's fresh/stale checks.
    // Empties on extension reactivation (window reload), so mutes can't silently
    // persist; rebuilding a scenario's outputs un-mutes that scenario. Purely a
    // local view — never written to files or git.
    private mutedScenarios = new Set<string>();

    constructor(private workspaceRoot: string | undefined) {
        // Update when active editor changes
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor(editor => {
                this.updateCurrentScenario(editor);
            })
        );

        // Watch for BTN file changes to clear metadata cache
        if (workspaceRoot) {
            const btnWatcher = vscode.workspace.createFileSystemWatcher(
                new vscode.RelativePattern(workspaceRoot, 'btn/*.btn')
            );
            btnWatcher.onDidChange(() => {
                clearMetadataCache();
                this.refresh();
            });
            btnWatcher.onDidCreate(() => {
                clearMetadataCache();
                this.refresh();
            });
            btnWatcher.onDidDelete(() => {
                clearMetadataCache();
                this.refresh();
            });
            this.disposables.push(btnWatcher);
        }

        // Initial update
        this.updateCurrentScenario(vscode.window.activeTextEditor);
    }

    private updateCurrentScenario(editor: vscode.TextEditor | undefined): void {
        const oldScenario = this.currentScenario;

        if (editor) {
            const newScenario = getScenarioFromPath(editor.document.uri.fsPath);
            // Only update if we found a valid scenario (keep previous when switching to non-scenario files)
            if (newScenario) {
                this.currentScenario = newScenario;
            }
        }

        // Only refresh if scenario changed
        if (oldScenario !== this.currentScenario) {
            this._onDidChangeTreeData.fire();
        }
    }

    /**
     * The scenario this panel is showing, which is the last scenario file the
     * editor was on. It is deliberately sticky -- switching to a README does
     * not clear it -- so it answers "which scenario am I working on?" when the
     * active editor cannot, such as from the command palette or a tree view.
     */
    getCurrentScenario(): string | undefined {
        return this.currentScenario;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    /** True if the given scenario's freshness checks are currently muted. */
    private isMuted(scenario: string | undefined): boolean {
        return !!scenario && this.mutedScenarios.has(scenario);
    }

    /**
     * Toggle the fresh/stale indicators for the CURRENTLY shown scenario only.
     * Muting requires a modal confirm (it removes a safety hint); un-muting is
     * immediate. Per-scenario and session-scoped — other scenarios are unaffected,
     * nothing is written to files or git, and all mutes reset on window reload.
     */
    async toggleStalenessChecks(): Promise<void> {
        const scenario = this.currentScenario;
        if (!scenario) {
            vscode.window.showInformationMessage('Open a scenario file first to mute its freshness checks.');
            return;
        }
        if (!this.mutedScenarios.has(scenario)) {
            const choice = await vscode.window.showWarningMessage(
                `Mute stale (out-of-date) warnings for "${scenario}"?`,
                {
                    modal: true,
                    detail: 'Only this scenario is affected. Its out-of-date warnings stop showing (fresh and missing still show normally) until you restore them, run the pipeline on this scenario, or reload the window. Local view only — nothing in the files or git.'
                },
                'Mute'
            );
            if (choice !== 'Mute') {
                return;
            }
            this.mutedScenarios.add(scenario);
        } else {
            this.mutedScenarios.delete(scenario);
        }
        this.refresh();
    }

    /**
     * Restore true freshness indicators for a scenario — called when its output
     * artifacts are (re)built. No-op for scenarios that weren't muted.
     */
    unmuteScenario(scenario: string): void {
        this.mutedScenarios.delete(scenario);
        this.refresh();
    }

    dispose(): void {
        this.disposables.forEach(d => d.dispose());
    }

    getTreeItem(element: ScenarioTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ScenarioTreeItem): Thenable<ScenarioTreeItem[]> {
        if (!this.workspaceRoot || !this.currentScenario) {
            return Promise.resolve([]);
        }

        if (!element) {
            // Root level - return the scenario header
            return Promise.resolve([
                new ScenarioTreeItem(
                    `Scenario: ${this.currentScenario}`,
                    vscode.TreeItemCollapsibleState.Expanded,
                    true
                )
            ]);
        }

        if (element.isRoot) {
            // First add the BTN source file
            const btnPath = path.join(this.workspaceRoot!, 'btn', `${this.currentScenario!}.btn`);
            const btnExists = fs.existsSync(btnPath);
            const btnItem = new ScenarioTreeItem(
                'BTN',
                vscode.TreeItemCollapsibleState.None,
                false,
                undefined  // No artifactInfo - this is the source
            );
            btnItem.iconPath = new vscode.ThemeIcon('file-code');
            btnItem.contextValue = 'source';
            btnItem.resourceUri = vscode.Uri.file(btnPath);
            if (btnExists) {
                btnItem.command = {
                    command: 'pbs.openPbsFile',
                    title: 'Open BTN source',
                    arguments: [btnPath]
                };
                btnItem.tooltip = new vscode.MarkdownString(`**BTN Source**\n\n\`${btnPath}\`\n\n*Click to open*`);
            } else {
                btnItem.tooltip = new vscode.MarkdownString(`**BTN Source**\n\nNot found: \`${btnPath}\``);
            }

            // Get scenario metadata to filter artifacts
            const metadata = getBtnMetadata(this.currentScenario!, this.workspaceRoot!);

            // Filter artifacts based on bbaWorks, and on whether the scenario is leveled
            const leveled = isLeveled(this.currentScenario!, this.workspaceRoot!);
            const visibleArtifacts = ARTIFACTS.filter(artifact =>
                (!artifact.requiresBba || metadata.bbaWorks) &&
                (!artifact.requiresLeveled || leveled)
            );

            // Build artifact children
            const items: ScenarioTreeItem[] = [];

            for (const artifact of visibleArtifacts) {
                const info = this.getArtifactInfo(artifact, this.currentScenario!, this.workspaceRoot!);
                items.push(new ScenarioTreeItem(
                    info.shortName,
                    vscode.TreeItemCollapsibleState.None,
                    false,
                    info
                ));
            }

            // When this scenario's stale warnings are muted, lead with a loud,
            // clickable banner so the muted state is never silent.
            const leadIn: ScenarioTreeItem[] = [];
            if (this.isMuted(this.currentScenario)) {
                const banner = new ScenarioTreeItem(
                    'Stale warnings muted — click to restore',
                    vscode.TreeItemCollapsibleState.None,
                    false,
                    undefined
                );
                banner.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('editorWarning.foreground'));
                banner.command = { command: 'pbs.toggleStalenessChecks', title: 'Restore stale warnings' };
                banner.tooltip = new vscode.MarkdownString('Out-of-date (stale) warnings for this scenario are muted — fresh and missing still show normally. Local view only; restored when you rebuild this scenario or reload the window.\n\n*Click to restore.*');
                banner.contextValue = 'stalenessBanner';
                leadIn.push(banner);
            }

            return Promise.resolve([...leadIn, btnItem, ...items]);
        }

        return Promise.resolve([]);
    }

    private getArtifactInfo(artifact: typeof ARTIFACTS[0], scenario: string, root: string): ArtifactInfo {
        const artifactPath = artifact.getPath(scenario, root);
        const sourcePath = artifact.getSourcePath(scenario, root);

        let status: ArtifactStatus = 'missing';
        let detail: string | undefined;

        if ((artifact as { fromStamp?: boolean }).fromStamp) {
            // The deal file is both the artifact and its own source here, so
            // the stamp decides, not the timestamps.
            if (fs.existsSync(artifactPath)) {
                const stamp = readSolvedStamp(artifactPath);
                if (stamp && stamp.solved >= stamp.deals) {
                    status = 'fresh';
                    detail = `${stamp.deals} deals solved`;
                } else if (stamp) {
                    status = 'stale';
                    detail = `${stamp.solved} of ${stamp.deals} deals solved`;
                } else {
                    status = 'stale';
                    detail = 'dealt, not solved';
                }
                if (status === 'stale' && this.isMuted(scenario)) {
                    status = 'unchecked';
                }
            }
            return {
                name: artifact.name,
                shortName: artifact.shortName,
                status,
                command: artifact.command,
                artifactPath,
                detail
            };
        }

        if (fs.existsSync(artifactPath)) {
            // Artifact exists - check if fresh or stale
            if (fs.existsSync(sourcePath)) {
                const artifactMtime = fs.statSync(artifactPath).mtimeMs;
                const sourceMtime = fs.statSync(sourcePath).mtimeMs;
                status = artifactMtime >= sourceMtime - FRESHNESS_TOLERANCE_MS ? 'fresh' : 'stale';
            } else {
                // No source to compare against - consider fresh
                status = 'fresh';
            }
            // Muting silences only the STALE warnings — fresh stays green, missing stays flagged.
            if (status === 'stale' && this.isMuted(scenario)) {
                status = 'unchecked';
            }
        }

        return {
            name: artifact.name,
            shortName: artifact.shortName,
            status,
            command: artifact.command,
            artifactPath
        };
    }
}
