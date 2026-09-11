import * as vscode from 'vscode';
import * as path from 'path';
import { activityLogger } from './extension';
import { getScenarioFromPath } from './scenarioPaths';

/**
 * Get the current scenario from the active editor
 */
function getCurrentScenario(): string | undefined {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return undefined;
    }

    const scenario = getScenarioFromPath(editor.document.uri.fsPath);
    if (!scenario) {
        vscode.window.showWarningMessage('Current file is not a PBS scenario');
        return undefined;
    }

    return scenario;
}

/**
 * Run the pipeline with specified operations
 */
async function runPipeline(scenario: string, operations: string): Promise<void> {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const scriptPath = path.join(workspaceFolder.uri.fsPath, 'build-scripts-mac', 'pbs-pipeline-mac.py');

    // Create or reuse terminal
    let terminal = vscode.window.terminals.find(t => t.name === 'PBS Pipeline');
    if (!terminal) {
        terminal = vscode.window.createTerminal('PBS Pipeline');
    }

    terminal.show();

    // Log pipeline run for activity tracking
    if (activityLogger) {
        activityLogger.logPipelineRun(scenario, operations);
    }

    terminal.sendText(`cd "${workspaceFolder.uri.fsPath}" && python3 "${scriptPath}" "${scenario}" "${operations}" -q`);
}

/**
 * Register a pipeline command
 */
function registerCommand(context: vscode.ExtensionContext, commandId: string, operations: string): void {
    context.subscriptions.push(
        vscode.commands.registerCommand(commandId, async () => {
            const scenario = getCurrentScenario();
            if (scenario) {
                await runPipeline(scenario, operations);
            }
        })
    );
}

/**
 * Register all pipeline commands
 */
export function registerPipelineCommands(context: vscode.ExtensionContext): void {
    // All operations
    registerCommand(context, 'pbs.runAll', '*');

    // Individual operations
    registerCommand(context, 'pbs.runDlr', 'dlr');
    registerCommand(context, 'pbs.runLevel', 'level');
    registerCommand(context, 'pbs.runPbn', 'pbn');
    registerCommand(context, 'pbs.runRotate', 'rotate');
    registerCommand(context, 'pbs.runBba', 'bba');
    registerCommand(context, 'pbs.runFilter', 'filter');
    registerCommand(context, 'pbs.runFilterStats', 'filterStats');
    registerCommand(context, 'pbs.runBiddingSheet', 'biddingSheet');
    registerCommand(context, 'pbs.runQuiz', 'quiz');
    registerCommand(context, 'pbs.runPackage', 'package');

    // Plus operations (from X through end)
    registerCommand(context, 'pbs.runDlrPlus', 'dlr+');
    registerCommand(context, 'pbs.runLevelPlus', 'level+');
    registerCommand(context, 'pbs.runPbnPlus', 'pbn+');
    registerCommand(context, 'pbs.runRotatePlus', 'rotate+');
    registerCommand(context, 'pbs.runBbaPlus', 'bba+');
    registerCommand(context, 'pbs.runFilterPlus', 'filter+');
    registerCommand(context, 'pbs.runFilterStatsPlus', 'filterStats+');
    registerCommand(context, 'pbs.runQuizPlus', 'quiz+');
    registerCommand(context, 'pbs.runPackagePlus', 'package+');

    // Release operation (not included in wildcards - must be explicit).
    // Publishes the scenario: commits and pushes btn/<name>.btn + dlr/<name>.dlr
    // (and dlr-leveled/<name>.dlr when leveled) to main, which is what the BBO
    // extension loads.
    context.subscriptions.push(
        vscode.commands.registerCommand('pbs.runRelease', async () => {
            const scenario = getCurrentScenario();
            if (!scenario) {
                return;
            }

            const confirm = await vscode.window.showInformationMessage(
                `Publish ${scenario}?`,
                {
                    modal: true,
                    detail: `Commits btn/${scenario}.btn and dlr/${scenario}.dlr, and dlr-leveled/${scenario}.dlr if the scenario is leveled, and pushes them to main. BBO users get the change as soon as the push lands.`
                },
                'Publish'
            );

            if (confirm !== 'Publish') {
                return;
            }

            await runPipeline(scenario, 'release');
        })
    );

    // Release layout operation (copies beta layout to release)
    context.subscriptions.push(
        vscode.commands.registerCommand('pbs.runReleaseLayout', async () => {
            const confirm = await vscode.window.showInformationMessage(
                'Release button layout to production?',
                { modal: true },
                'Release'
            );

            if (confirm !== 'Release') {
                return;
            }

            // Pass "layout" as dummy scenario - the operation ignores it
            await runPipeline('layout', 'release-layout');
        })
    );
}

/**
 * Status bar item showing current scenario
 */
let statusBarItem: vscode.StatusBarItem;

export function createStatusBar(context: vscode.ExtensionContext): void {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'pbs.runAll';
    context.subscriptions.push(statusBarItem);

    // Update status bar when active editor changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(updateStatusBar)
    );

    // Initial update
    updateStatusBar(vscode.window.activeTextEditor);
}

function updateStatusBar(editor: vscode.TextEditor | undefined): void {
    if (!statusBarItem) {
        return;
    }

    if (!editor) {
        statusBarItem.hide();
        return;
    }

    const scenario = getScenarioFromPath(editor.document.uri.fsPath);
    if (scenario) {
        statusBarItem.text = `$(play) PBS: ${scenario}`;
        statusBarItem.tooltip = `Click to run all operations on ${scenario}`;
        statusBarItem.show();
    } else {
        statusBarItem.hide();
    }
}
