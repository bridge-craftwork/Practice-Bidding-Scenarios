import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { getScenarioFromPath } from './scenarioPaths';

type ActivityType = 'file_save' | 'session_start' | 'session_end' | 'pipeline_run';

interface ActivityEventDetails {
    filePath?: string;
    fileType?: string;
    scenario?: string;
    operation?: string;
    durationMinutes?: number;
}

interface ActivityEvent {
    timestamp: string;
    type: ActivityType;
    details: ActivityEventDetails;
}

interface ActivityLog {
    version: number;
    workspacePath: string;
    events: ActivityEvent[];
}

/**
 * Maps file extensions and directory names to file types
 */
function getFileType(filePath: string): string | undefined {
    const ext = path.extname(filePath).toLowerCase();

    // Map extensions to types
    const extMap: { [key: string]: string } = {
        '.dlr': 'dlr',
        '.pbn': 'pbn',
        '.lin': 'lin',
        '.pdf': 'pdf',
        '.py': 'python',
        '.ts': 'typescript',
        '.js': 'javascript',
        '.json': 'json',
        '.html': 'html',
        '.css': 'css',
        '.md': 'markdown'
    };

    return extMap[ext] || ext.slice(1) || undefined;
}

/**
 * Activity logger for VSCode extension
 * Logs file saves, session time, and pipeline runs to a JSON file
 */
export class ActivityLogger {
    private logPath: string;
    private workspaceRoot: string;
    private sessionStartTime: Date | undefined;

    constructor(workspaceRoot: string | undefined) {
        this.workspaceRoot = workspaceRoot || '';
        this.logPath = path.join(this.workspaceRoot, 'activity-log.json');
    }

    /**
     * Record session start
     */
    startSession(): void {
        this.sessionStartTime = new Date();
        this.appendEvent({
            timestamp: this.sessionStartTime.toISOString(),
            type: 'session_start',
            details: {}
        });
    }

    /**
     * Record session end with duration
     */
    endSession(): void {
        const endTime = new Date();
        let durationMinutes: number | undefined;

        if (this.sessionStartTime) {
            durationMinutes = Math.round((endTime.getTime() - this.sessionStartTime.getTime()) / 60000);
        }

        this.appendEvent({
            timestamp: endTime.toISOString(),
            type: 'session_end',
            details: {
                durationMinutes
            }
        });
    }

    /**
     * Log a file save event
     */
    logFileSave(document: vscode.TextDocument): void {
        const filePath = document.uri.fsPath;

        // Only log files within the workspace
        if (!filePath.startsWith(this.workspaceRoot)) {
            return;
        }

        const relativePath = path.relative(this.workspaceRoot, filePath);
        const fileType = getFileType(filePath);
        const scenario = getScenarioFromPath(filePath);

        this.appendEvent({
            timestamp: new Date().toISOString(),
            type: 'file_save',
            details: {
                filePath: relativePath,
                fileType,
                scenario
            }
        });
    }

    /**
     * Log a pipeline run
     */
    logPipelineRun(scenario: string, operation: string): void {
        this.appendEvent({
            timestamp: new Date().toISOString(),
            type: 'pipeline_run',
            details: {
                scenario,
                operation
            }
        });
    }

    /**
     * Append an event to the log file
     */
    private appendEvent(event: ActivityEvent): void {
        try {
            const log = this.readLog();
            log.events.push(event);
            this.writeLog(log);
        } catch (error) {
            console.error('ActivityLogger: Failed to append event', error);
        }
    }

    /**
     * Read existing log or create new one
     */
    private readLog(): ActivityLog {
        try {
            if (fs.existsSync(this.logPath)) {
                const content = fs.readFileSync(this.logPath, 'utf8');
                return JSON.parse(content);
            }
        } catch (error) {
            console.error('ActivityLogger: Failed to read log, creating new', error);
        }

        return {
            version: 1,
            workspacePath: this.workspaceRoot,
            events: []
        };
    }

    /**
     * Write log to disk
     */
    private writeLog(log: ActivityLog): void {
        try {
            fs.writeFileSync(this.logPath, JSON.stringify(log, null, 2), 'utf8');
        } catch (error) {
            console.error('ActivityLogger: Failed to write log', error);
        }
    }
}
