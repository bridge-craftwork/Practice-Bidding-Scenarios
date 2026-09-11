import * as vscode from 'vscode';
import { ButtonPanelProvider } from './buttonPanelProvider';
import { ButtonGridProvider } from './buttonGridProvider';
import { CurrentScenarioProvider, ScenarioTreeItem } from './currentScenarioProvider';
import { registerPipelineCommands, createStatusBar } from './pipelineRunner';
import { ActivityLogger } from './activityLogger';
import { getBtnMetadata, clearMetadataCache } from './btnParser';
import { getScenarioFromPath } from './scenarioPaths';

// Export logger instance for use by other modules (e.g., pipelineRunner)
export let activityLogger: ActivityLogger | undefined;

/**
 * Update the pbs.bbaWorks context variable based on current editor
 */
function updateBbaWorksContext(editor: vscode.TextEditor | undefined, workspaceRoot: string | undefined): void {
    if (!workspaceRoot || !editor) {
        vscode.commands.executeCommand('setContext', 'pbs.bbaWorks', false);
        return;
    }

    const scenario = getScenarioFromPath(editor.document.uri.fsPath);
    if (!scenario) {
        // Not a scenario file - default to false (hide BBA options)
        vscode.commands.executeCommand('setContext', 'pbs.bbaWorks', false);
        return;
    }

    const metadata = getBtnMetadata(scenario, workspaceRoot);
    vscode.commands.executeCommand('setContext', 'pbs.bbaWorks', metadata.bbaWorks);
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Practice Bidding Scenarios extension is now active');

    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    // Initialize activity logger and start session
    activityLogger = new ActivityLogger(workspaceRoot);
    activityLogger.startSession();

    // Register dispose callback to end session when extension deactivates
    context.subscriptions.push({
        dispose: () => {
            if (activityLogger) {
                activityLogger.endSession();
            }
        }
    });

    // Log file saves for activity tracking
    const saveWatcher = vscode.workspace.onDidSaveTextDocument(document => {
        if (activityLogger) {
            activityLogger.logFileSave(document);
        }
    });
    context.subscriptions.push(saveWatcher);

    // Create the current scenario provider (shows focused scenario with artifact status)
    const currentScenarioProvider = new CurrentScenarioProvider(workspaceRoot);

    // Register the current scenario tree view
    const currentScenarioView = vscode.window.createTreeView('pbsCurrentScenario', {
        treeDataProvider: currentScenarioProvider,
        showCollapseAll: false
    });

    // When a scenario's OUTPUT artifacts are (re)built, restore its true freshness
    // indicators. Running the pipe on one scenario un-mutes only that scenario;
    // others keep whatever mute state they had.
    const restoreFreshnessOnBuild = (uri: vscode.Uri) => {
        const scenario = getScenarioFromPath(uri.fsPath);
        if (scenario) {
            currentScenarioProvider.unmuteScenario(scenario);
        } else {
            currentScenarioProvider.refresh();
        }
    };

    // Update bbaWorks context when active editor changes
    const editorChangeListener = vscode.window.onDidChangeActiveTextEditor(editor => {
        updateBbaWorksContext(editor, workspaceRoot);
    });
    context.subscriptions.push(editorChangeListener);

    // Initial context update
    updateBbaWorksContext(vscode.window.activeTextEditor, workspaceRoot);

    // Create the button panel provider (tree view)
    const buttonPanelProvider = new ButtonPanelProvider(workspaceRoot);

    // Register the tree view
    const treeView = vscode.window.createTreeView('pbsButtonPanel', {
        treeDataProvider: buttonPanelProvider,
        showCollapseAll: true
    });

    // Create the button grid provider (webview)
    const buttonGridProvider = new ButtonGridProvider(context.extensionUri, workspaceRoot);

    // Register the webview view provider
    const webviewProvider = vscode.window.registerWebviewViewProvider(
        ButtonGridProvider.viewType,
        buttonGridProvider
    );

    // Register refresh command for tree view
    const refreshCommand = vscode.commands.registerCommand('pbs.refreshButtonPanel', () => {
        buttonPanelProvider.refresh();
        vscode.window.showInformationMessage('PBS Tree View refreshed');
    });

    // Register refresh command for button grid
    const refreshGridCommand = vscode.commands.registerCommand('pbs.refreshButtonGrid', () => {
        buttonGridProvider.refresh();
        vscode.window.showInformationMessage('PBS Button Grid refreshed');
    });

    // Register rebuild artifact command (for right-click context menu)
    const rebuildArtifactCommand = vscode.commands.registerCommand('pbs.rebuildArtifact', async (item: ScenarioTreeItem) => {
        if (item?.artifactInfo?.command) {
            await vscode.commands.executeCommand(item.artifactInfo.command);
        }
    });

    // Register toggle for the Current Scenario freshness (fresh/stale) indicators.
    // Confirm-on-disable lives in the provider; the muted state auto-re-arms on reload.
    const toggleStalenessCommand = vscode.commands.registerCommand('pbs.toggleStalenessChecks', async () => {
        await currentScenarioProvider.toggleStalenessChecks();
    });

    // Register open file command
    const openFileCommand = vscode.commands.registerCommand('pbs.openPbsFile', async (filePath: string, lineNumber?: number) => {
        if (!filePath) {
            return;
        }

        try {
            const document = await vscode.workspace.openTextDocument(filePath);
            const editor = await vscode.window.showTextDocument(document);

            if (lineNumber && lineNumber > 0) {
                const position = new vscode.Position(lineNumber - 1, 0);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to open file: ${filePath}`);
        }
    });

    // Watch BTN files: clear the metadata cache, update context, and rebuild
    // the Scenarios tree and Button Grid (both are built from btn/*.btn)
    const onBtnChange = () => {
        clearMetadataCache();
        updateBbaWorksContext(vscode.window.activeTextEditor, workspaceRoot);
        buttonPanelProvider.refresh();
        buttonGridProvider.refresh();
    };
    const btnWatcher = vscode.workspace.createFileSystemWatcher('**/btn/*.btn');
    btnWatcher.onDidChange(onBtnChange);
    btnWatcher.onDidCreate(onBtnChange);
    btnWatcher.onDidDelete(onBtnChange);

    // Watch the button layout file (section structure) and the legacy main config
    const refreshButtonViews = () => {
        buttonPanelProvider.refresh();
        buttonGridProvider.refresh();
    };
    const layoutWatcher = vscode.workspace.createFileSystemWatcher('**/btn/-button-layout-release.txt');
    layoutWatcher.onDidChange(refreshButtonViews);
    layoutWatcher.onDidCreate(refreshButtonViews);
    layoutWatcher.onDidDelete(refreshButtonViews);
    const configWatcher = vscode.workspace.createFileSystemWatcher('**/-PBS.txt');
    configWatcher.onDidChange(refreshButtonViews);

    // Watch artifact directories for current scenario status updates
    const artifactWatcher = vscode.workspace.createFileSystemWatcher('**/{dlr,pbn,pbn-rotated-for-4-players,bba,bba-filtered,bidding-sheets,quiz}/*');
    artifactWatcher.onDidChange(restoreFreshnessOnBuild);
    artifactWatcher.onDidCreate(restoreFreshnessOnBuild);
    artifactWatcher.onDidDelete(() => currentScenarioProvider.refresh());

    // Watch Bidding Scenarios folder for package artifact status updates
    const packageWatcher = vscode.workspace.createFileSystemWatcher('**/Bidding Scenarios/**/*');
    packageWatcher.onDidChange(() => currentScenarioProvider.refresh());
    packageWatcher.onDidCreate(() => currentScenarioProvider.refresh());
    packageWatcher.onDidDelete(() => currentScenarioProvider.refresh());

    context.subscriptions.push(
        currentScenarioView,
        treeView,
        webviewProvider,
        refreshCommand,
        refreshGridCommand,
        rebuildArtifactCommand,
        toggleStalenessCommand,
        openFileCommand,
        btnWatcher,
        layoutWatcher,
        configWatcher,
        artifactWatcher,
        packageWatcher
    );

    // Register pipeline commands and status bar
    registerPipelineCommands(context);
    createStatusBar(context);

    // Explicit startup refresh to catch changes made while VS Code was closed
    // Small delay ensures views are fully registered before refreshing
    setTimeout(() => {
        buttonPanelProvider.refresh();
        buttonGridProvider.refresh();
        currentScenarioProvider.refresh();
        console.log('PBS Dashboard refreshed on startup');
    }, 500);
}

export function deactivate() {}
