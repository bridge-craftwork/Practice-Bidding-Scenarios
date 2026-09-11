import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { PbsSection, parseButtonLayoutFile } from './pbsParser';
import { parseBtnDirectory, resolveLayoutSections } from './btnParser';

/** Escape text for use in HTML content or a double-quoted attribute */
function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export class ButtonGridProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'pbsButtonGrid';

    private _view?: vscode.WebviewView;
    private sections: PbsSection[] = [];

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly workspaceRoot: string | undefined
    ) {
        this.loadData();
    }

    public async resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'openFile':
                    if (data.filePath) {
                        const document = await vscode.workspace.openTextDocument(data.filePath);
                        const editor = await vscode.window.showTextDocument(document);

                        if (data.lineNumber && data.lineNumber > 0) {
                            const position = new vscode.Position(data.lineNumber - 1, 0);
                            editor.selection = new vscode.Selection(position, position);
                            editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);
                        }
                    }
                    break;
            }
        });
    }

    public refresh() {
        this.loadData();
        if (this._view) {
            this._view.webview.html = this._getHtmlForWebview(this._view.webview);
        }
    }

    private loadData() {
        if (!this.workspaceRoot) {
            return;
        }

        // One button per btn/*.btn master file; the layout file gives the sections
        const buttons = parseBtnDirectory(path.join(this.workspaceRoot, 'btn'));

        const layoutPath = path.join(this.workspaceRoot, 'btn', '-button-layout-release.txt');
        if (fs.existsSync(layoutPath)) {
            this.sections = parseButtonLayoutFile(layoutPath);
            resolveLayoutSections(this.sections, buttons);
        } else {
            // No layout file, create a single section with all buttons
            this.sections = [{
                title: 'PBS Buttons',
                buttons: buttons,
                backgroundColor: 'lightblue'
            }];
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const sectionsHtml = this.sections.map((section, index) => {
            const buttonsHtml = section.buttons
                .filter(button => button.label) // Keep all buttons including '---' placeholders
                .map(button => {
                    // Check if this is a placeholder button
                    const isPlaceholder = button.label === '---';
                    const bgColor = button.backgroundColor || 'white';

                    // Determine width for button sizing
                    // Subtract gap space from percentages to prevent wrapping
                    let width: string;
                    const labelLength = button.label.trim().length;

                    if (button.width) {
                        if (button.width.endsWith('%')) {
                            const percent = parseInt(button.width);
                            // Subtract 4px per button to account for gaps
                            width = `calc(${percent}% - 4px)`;
                        } else {
                            width = button.width;
                        }
                    } else if (labelLength <= 2) {
                        width = '32px'; // Very short labels (1, 2, 3, 4)
                    } else {
                        width = 'calc(50% - 4px)'; // Default 2 per row
                    }

                    const escapedFilePath = button.filePath ? button.filePath.replace(/'/g, "\\'") : '';
                    const lineNumber = button.lineNumber || 0;

                    if (isPlaceholder) {
                        // Render placeholder - use same width as regular buttons
                        return `<button
                            class="pbs-button pbs-placeholder"
                            style="background-color: ${bgColor}; width: calc(50% - 4px);"
                            disabled
                        >--</button>`;
                    }

                    return `<button
                        class="pbs-button"
                        style="background-color: ${bgColor}; width: ${width};"
                        onclick="openFile('${escapedFilePath}', ${lineNumber})"
                        title="${escapeHtml(button.description || button.label)}"
                    >${escapeHtml(button.label)}</button>`;
                }).join('\n');

            const headerBgColor = section.backgroundColor || 'lightblue';

            return `
                <div class="section">
                    <button class="section-header" style="background-color: ${headerBgColor};" onclick="toggleSection(${index})">
                        <span class="collapse-icon" id="icon-${index}">▶</span>
                        ${section.title}
                    </button>
                    <div class="section-content" id="section-${index}" style="display: none;">
                        ${buttonsHtml}
                    </div>
                </div>
            `;
        }).join('\n');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            padding: 4px;
            margin: 0;
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
        }

        .section {
            margin-bottom: 4px;
        }

        .section-header {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            cursor: pointer;
            text-align: left;
            font-weight: bold;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-header:hover {
            opacity: 0.9;
        }

        .collapse-icon {
            font-size: 10px;
            transition: transform 0.2s;
        }

        .collapse-icon.expanded {
            transform: rotate(90deg);
        }

        .section-content {
            padding: 4px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }

        .pbs-button {
            padding: 6px 10px;
            border: 1px solid #999;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            text-align: center;
            color: #000;
            box-sizing: border-box;
        }

        .pbs-button:hover:not(:disabled) {
            opacity: 0.85;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .pbs-placeholder {
            cursor: default;
            opacity: 0.5;
            color: #666;
        }
    </style>
</head>
<body>
    ${sectionsHtml}

    <script>
        const vscode = acquireVsCodeApi();

        function toggleSection(index) {
            const content = document.getElementById('section-' + index);
            const icon = document.getElementById('icon-' + index);

            if (content.style.display === 'none') {
                content.style.display = 'flex';
                icon.classList.add('expanded');
            } else {
                content.style.display = 'none';
                icon.classList.remove('expanded');
            }
        }

        function openFile(filePath, lineNumber) {
            if (filePath) {
                vscode.postMessage({
                    type: 'openFile',
                    filePath: filePath,
                    lineNumber: lineNumber
                });
            }
        }
    </script>
</body>
</html>`;
    }
}
