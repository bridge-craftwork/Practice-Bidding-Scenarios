import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { PbsButton, PbsSection, parseButtonLayoutFile, parseMainPbsConfig } from './pbsParser';
import { parseBtnDirectory, resolveLayoutSections } from './btnParser';

/**
 * Tree item representing either a section header or a button
 */
export class PbsTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly button?: PbsButton,
        public readonly isSection: boolean = false,
        public readonly sectionColor?: string
    ) {
        super(label, collapsibleState);

        if (button && button.filePath) {
            this.tooltip = this.createTooltip(button);
            this.command = {
                command: 'pbs.openPbsFile',
                title: 'Open PBS File',
                arguments: [button.filePath, button.lineNumber]
            };

            // Set icon based on background color
            // lightpink = convention not known by GIB (show warning icon)
            // lightgreen = control buttons (no icon)
            // no color = regular scenario (no icon)
            if (button.backgroundColor === 'lightpink') {
                this.iconPath = new vscode.ThemeIcon('circle-slash', new vscode.ThemeColor('errorForeground'));
            }
            // No icon for lightgreen (control buttons) or regular scenarios
        } else if (isSection) {
            // Section header styling
            if (sectionColor === 'lightblue') {
                this.iconPath = new vscode.ThemeIcon('folder', new vscode.ThemeColor('charts.blue'));
            } else if (sectionColor === 'LemonChiffon') {
                this.iconPath = new vscode.ThemeIcon('folder', new vscode.ThemeColor('charts.yellow'));
            } else if (sectionColor === 'gray') {
                this.iconPath = new vscode.ThemeIcon('question', new vscode.ThemeColor('disabledForeground'));
            } else {
                this.iconPath = new vscode.ThemeIcon('folder');
            }
        }
    }

    private createTooltip(button: PbsButton): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.appendMarkdown(`**${button.label}**\n\n`);

        if (button.description) {
            // Convert bridge notation to Unicode symbols for display
            const description = button.description
                .replace(/!S/g, '\u2660')  // Spade
                .replace(/!H/g, '\u2665')  // Heart
                .replace(/!D/g, '\u2666')  // Diamond
                .replace(/!C/g, '\u2663'); // Club
            md.appendText(description);
            md.appendMarkdown('\n\n');
        }

        if (button.scriptId) {
            md.appendMarkdown(`*Script: ${button.scriptId}*\n`);
        }

        if (button.filePath) {
            md.appendMarkdown(`\n---\n*Click to open file*`);
        }

        return md;
    }
}

/**
 * TreeDataProvider for the PBS Button Panel sidebar
 */
export class ButtonPanelProvider implements vscode.TreeDataProvider<PbsTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<PbsTreeItem | undefined | null | void> = new vscode.EventEmitter<PbsTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<PbsTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private sections: PbsSection[] = [];
    private unmappedButtons: PbsButton[] = [];

    constructor(private workspaceRoot: string | undefined) {
        this.loadData().then(() => {
            this._onDidChangeTreeData.fire();
        });
    }

    refresh(): void {
        this.loadData().then(() => {
            this._onDidChangeTreeData.fire();
        });
    }

    private async loadData(): Promise<void> {
        if (!this.workspaceRoot) {
            return;
        }

        // One button per btn/*.btn master file
        const buttons = parseBtnDirectory(path.join(this.workspaceRoot, 'btn'));

        // Section structure: btn/-button-layout-release.txt, else legacy -PBS.txt
        const layoutPath = path.join(this.workspaceRoot, 'btn', '-button-layout-release.txt');
        const mainConfigPath = path.join(this.workspaceRoot, '-PBS.txt');

        if (fs.existsSync(layoutPath)) {
            this.sections = parseButtonLayoutFile(layoutPath);
        } else if (fs.existsSync(mainConfigPath)) {
            this.sections = parseMainPbsConfig(mainConfigPath);
        } else {
            this.sections = [];
        }

        if (this.sections.length > 0) {
            const mappedFilePaths = resolveLayoutSections(this.sections, buttons);

            // Unmapped: .btn files not referenced in any section
            this.unmappedButtons = buttons.filter(btn =>
                btn.filePath &&
                btn.label &&
                btn.label.trim() !== '' &&
                !mappedFilePaths.has(btn.filePath)
            );
        } else {
            // No layout, create a single section with all buttons
            this.unmappedButtons = [];
            this.sections = [{
                title: 'PBS Buttons',
                buttons: buttons,
                backgroundColor: 'lightblue'
            }];
        }
    }

    getTreeItem(element: PbsTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: PbsTreeItem): Thenable<PbsTreeItem[]> {
        if (!this.workspaceRoot) {
            vscode.window.showInformationMessage('No workspace folder open');
            return Promise.resolve([]);
        }

        if (!element) {
            // Root level - return sections
            const items: PbsTreeItem[] = [];

            // Add regular sections
            const validSections = this.sections.filter(section =>
                section.title && section.title.trim() !== ''
            );

            for (const section of validSections) {
                items.push(new PbsTreeItem(
                    section.title,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    undefined,
                    true,
                    section.backgroundColor
                ));
            }

            // Add Unmapped section at the bottom if there are unmapped files
            if (this.unmappedButtons.length > 0) {
                items.push(new PbsTreeItem(
                    `Unmapped (${this.unmappedButtons.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    undefined,
                    true,
                    'gray'
                ));
            }

            return Promise.resolve(items);
        }

        // Check if this is the Unmapped section
        if (element.label?.startsWith('Unmapped')) {
            return Promise.resolve(
                this.unmappedButtons
                    .filter(button => button.label && button.label.trim() !== '' && button.label !== '---')
                    .sort((a, b) => a.label.localeCompare(b.label))
                    .map(button => new PbsTreeItem(
                        button.label,
                        vscode.TreeItemCollapsibleState.None,
                        button,
                        false
                    ))
            );
        }

        // Return buttons in the section
        const section = this.sections.find(s => s.title === element.label);
        if (section) {
            return Promise.resolve(
                section.buttons
                    .filter(button => button.label && button.label.trim() !== '' && button.label !== '---')
                    .map(button => new PbsTreeItem(
                        button.label,
                        vscode.TreeItemCollapsibleState.None,
                        button,
                        false
                    ))
            );
        }

        return Promise.resolve([]);
    }
}
