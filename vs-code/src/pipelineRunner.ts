import * as vscode from 'vscode';
import * as path from 'path';
import { activityLogger } from './extension';
import { getScenarioFromPath } from './scenarioPaths';

/**
 * The scenario the PBS panel is showing, set at activation. It is the fallback
 * when the active editor cannot name one.
 */
let panelScenario: () => string | undefined = () => undefined;

/**
 * Which scenario a command should run on.
 *
 * The active editor answers this when a scenario file is open and focused. It
 * cannot when focus is anywhere else -- the command palette, a tree view, the
 * button grid, a PDF -- and a command run from the palette used to fail there
 * with "No active editor", which described the editor rather than the problem.
 *
 * So fall back to the scenario the PBS panel is showing. That panel holds the
 * last scenario file the editor was on, and says so on screen, which makes it
 * the honest answer to "which scenario am I working on?".
 */
function getCurrentScenario(): string | undefined {
    const editor = vscode.window.activeTextEditor;
    const fromEditor = editor && getScenarioFromPath(editor.document.uri.fsPath);
    if (fromEditor) {
        return fromEditor;
    }

    const fromPanel = panelScenario();
    if (fromPanel) {
        return fromPanel;
    }

    vscode.window.showWarningMessage(
        'No scenario selected. Open one from btn/, dlr/ or pbn/, or click a scenario ' +
        'in the PBS panel, then run this again.');
    return undefined;
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
export function registerPipelineCommands(
    context: vscode.ExtensionContext,
    currentScenario?: () => string | undefined,
): void {
    if (currentScenario) {
        panelScenario = currentScenario;
    }
    // All operations
    registerCommand(context, 'pbs.runAll', '*');

    // Individual operations
    registerCommand(context, 'pbs.runDlr', 'dlr');
    registerCommand(context, 'pbs.runLevel', 'level');
    registerCommand(context, 'pbs.runPbn', 'pbn');
    registerCommand(context, 'pbs.runSolve', 'solve');
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
    registerCommand(context, 'pbs.runSolvePlus', 'solve+');
    registerCommand(context, 'pbs.runRotatePlus', 'rotate+');
    registerCommand(context, 'pbs.runBbaPlus', 'bba+');
    registerCommand(context, 'pbs.runFilterPlus', 'filter+');
    registerCommand(context, 'pbs.runFilterStatsPlus', 'filterStats+');
    registerCommand(context, 'pbs.runQuizPlus', 'quiz+');
    registerCommand(context, 'pbs.runPackagePlus', 'package+');

    // BBO demo (explicit-only, like release, and never in a wildcard run).
    // Opens a four-robot table on BBO with this scenario's script loaded and
    // captures nothing, so a script can be tried by hand -- redealing, reading
    // the robots' explanations -- before it is published. Closing the BBO tab
    // ends it. One scenario at a time: the pipeline refuses more, because we
    // are guests on BBO.
    registerCommand(context, 'pbs.runBboDemo', 'bbo-demo');

    // gibReport reads the capture already in GIB/ and writes the filtered
    // files and the report. Local only, so it runs on a click like any other
    // operation -- and it is the one to reach for after editing a filter.
    registerCommand(context, 'pbs.runGibReport', 'gibReport');

    // gib replaces that capture by having BBO's robots bid 30 boards on a live
    // account, so it asks first: it costs someone else's server time, and a
    // misclick beside the local operations would spend it silently. Also
    // explicit-only, and one scenario at a time.
    context.subscriptions.push(
        vscode.commands.registerCommand('pbs.runGib', async () => {
            const scenario = getCurrentScenario();
            if (!scenario) {
                return;
            }

            const confirm = await vscode.window.showInformationMessage(
                `Capture GIB auctions for ${scenario}?`,
                {
                    modal: true,
                    detail: `Has BBO's robots bid 30 boards from this scenario's script on a live account, replaces GIB/${scenario}.pbn with what they bid, and then runs the report. Keep live runs small: we are guests on BBO.`
                },
                'Capture'
            );

            if (confirm !== 'Capture') {
                return;
            }

            await runPipeline(scenario, 'gib');
        })
    );

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
