import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { execFile, execFileSync } from 'child_process';
import { promisify } from 'util';
import {
    downloadAndUnzipVSCode,
    resolveCliPathFromVSCodeExecutablePath,
    runTests,
} from '@vscode/test-electron';

const execFileAsync = promisify(execFile);

const extensionRoot = path.resolve(__dirname, '../..');
const suitePath = path.resolve(__dirname, './suite/index');
const publisherExtensionId = 'u9401066.asset-aware-mcp';
const packageJson = JSON.parse(
    fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'),
) as { version: string };
const currentVersion = packageJson.version;

async function runCommand(command: string, args: string[], cwd?: string): Promise<string> {
    const maxBuffer = 1024 * 1024 * 10;
    const isWindowsCmd = process.platform === 'win32' && path.extname(command).toLowerCase() === '.cmd';

    if (isWindowsCmd) {
        const quoteForCmd = (value: string): string => (
            /[\s"]/u.test(value) ? `"${value.replaceAll('"', '""')}"` : value
        );
        const commandLine = [quoteForCmd(command), ...args.map(quoteForCmd)].join(' ');
        const shellCommand = /[\s]/u.test(command) ? `"${commandLine}"` : commandLine;
        const { stdout, stderr } = await execFileAsync(process.env.ComSpec ?? 'cmd.exe', [
            '/d',
            '/s',
            '/c',
            shellCommand,
        ], {
            cwd,
            env: process.env,
            maxBuffer,
        });

        return `${stdout}${stderr}`.trim();
    }

    const { stdout, stderr } = await execFileAsync(command, args, {
        cwd,
        env: process.env,
        maxBuffer,
    });

    return `${stdout}${stderr}`.trim();
}

async function packageCurrentVsix(): Promise<string> {
    const vsixPath = path.join(extensionRoot, `asset-aware-mcp-${currentVersion}.vsix`);
    if (fs.existsSync(vsixPath)) {
        fs.rmSync(vsixPath, { force: true });
    }

    const npxCommand = process.platform === 'win32' ? 'npx.cmd' : 'npx';
    await runCommand(npxCommand, ['vsce', 'package', '--no-dependencies', '--out', vsixPath], extensionRoot);
    return vsixPath;
}

function findAvailableCli(): string | null {
    const candidates = process.platform === 'win32'
        ? ['code-insiders.cmd', 'code.cmd']
        : ['code-insiders', 'code', 'codium'];

    for (const candidate of candidates) {
        try {
            const command = process.platform === 'win32' ? 'where' : 'which';
            const output = execFileSync(command, [candidate], { encoding: 'utf8' }).trim();
            if (output) {
                return output.split(/\r?\n/)[0];
            }
        } catch {
            // Try the next CLI candidate.
        }
    }

    return null;
}

function createIsolatedDirs(prefix: string): { baseDir: string; userDataDir: string; extensionsDir: string; workspaceDir: string } {
    const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
    const userDataDir = path.join(baseDir, 'user-data');
    const extensionsDir = path.join(baseDir, 'extensions');
    const workspaceDir = path.join(baseDir, 'workspace');

    fs.mkdirSync(userDataDir, { recursive: true });
    fs.mkdirSync(extensionsDir, { recursive: true });
    fs.mkdirSync(workspaceDir, { recursive: true });

    return { baseDir, userDataDir, extensionsDir, workspaceDir };
}

async function installVsix(cliPath: string, vsixPath: string, userDataDir: string, extensionsDir: string): Promise<void> {
    await runCommand(cliPath, [
        '--user-data-dir', userDataDir,
        '--extensions-dir', extensionsDir,
        '--install-extension', vsixPath,
        '--force',
    ]);
}

async function listInstalledVersions(cliPath: string, userDataDir: string, extensionsDir: string): Promise<string[]> {
    const output = await runCommand(cliPath, [
        '--user-data-dir', userDataDir,
        '--extensions-dir', extensionsDir,
        '--list-extensions',
        '--show-versions',
    ]);

    return output
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
}

function assertInstalledVersion(lines: string[], expectedVersion: string): void {
    const expected = `${publisherExtensionId}@${expectedVersion}`;
    if (!lines.includes(expected)) {
        throw new Error(`Expected installed extension ${expected}, got: ${lines.join(', ')}`);
    }
}

function resolveActivationExtensionPath(extensionsDir: string, version: string): string {
    const exactCandidates = [
        `${publisherExtensionId}-${version}`,
        `${publisherExtensionId}@${version}`,
    ];
    const entries = fs.existsSync(extensionsDir) ? fs.readdirSync(extensionsDir) : [];

    for (const candidate of exactCandidates) {
        if (entries.includes(candidate)) {
            return path.join(extensionsDir, candidate);
        }
    }

    const matchingEntry = entries.find((candidate) =>
        candidate.startsWith(`${publisherExtensionId}-`) || candidate.startsWith(`${publisherExtensionId}@`),
    );
    if (matchingEntry) {
        return path.join(extensionsDir, matchingEntry);
    }

    console.warn(
        `Could not locate extracted extension under ${extensionsDir}; ` +
        'falling back to the workspace extension root for activation smoke.',
    );
    return extensionRoot;
}

async function verifyActivation(installedExtensionDir: string, vscodeExecutablePath: string): Promise<void> {
    const needsHeadlessDisplay = process.platform === 'linux' && !process.env.DISPLAY && !process.env.WAYLAND_DISPLAY;
    if (needsHeadlessDisplay && !process.env.CI) {
        console.log('Skipping activation smoke test on local Linux without DISPLAY/xvfb. Install/update checks still passed.');
        return;
    }

    await runTests({
        vscodeExecutablePath,
        extensionDevelopmentPath: installedExtensionDir,
        extensionTestsPath: suitePath,
        launchArgs: ['--disable-extensions'],
    });
}

async function main(): Promise<void> {
    const currentVsixPath = await packageCurrentVsix();
    const oldVsixPath = path.join(extensionRoot, 'asset-aware-mcp-0.2.10.vsix');
    const needsHeadlessDisplay = process.platform === 'linux' && !process.env.DISPLAY && !process.env.WAYLAND_DISPLAY;
    const shouldRunActivation = process.platform !== 'win32' && (!needsHeadlessDisplay || Boolean(process.env.CI));

    let vscodeExecutablePath: string | undefined;
    const localCliPath = findAvailableCli();
    let cliPath = localCliPath;

    if (!cliPath || shouldRunActivation || process.platform === 'win32') {
        vscodeExecutablePath = await downloadAndUnzipVSCode();
        cliPath = resolveCliPathFromVSCodeExecutablePath(vscodeExecutablePath);
    }

    if (!cliPath) {
        throw new Error('Could not find a VS Code CLI for install smoke testing.');
    }

    const fresh = createIsolatedDirs('asset-aware-fresh');
    await installVsix(cliPath, currentVsixPath, fresh.userDataDir, fresh.extensionsDir);
    const freshVersions = await listInstalledVersions(cliPath, fresh.userDataDir, fresh.extensionsDir);
    assertInstalledVersion(freshVersions, currentVersion);
    console.log(`Fresh install verified: ${publisherExtensionId}@${currentVersion}`);

    const update = createIsolatedDirs('asset-aware-update');
    if (fs.existsSync(oldVsixPath)) {
        await installVsix(cliPath, oldVsixPath, update.userDataDir, update.extensionsDir);
        const beforeUpdate = await listInstalledVersions(cliPath, update.userDataDir, update.extensionsDir);
        assertInstalledVersion(beforeUpdate, '0.2.10');
        console.log('Baseline install verified: u9401066.asset-aware-mcp@0.2.10');
    } else {
        console.log('Skipping baseline update verification because asset-aware-mcp-0.2.10.vsix is not available.');
    }

    await installVsix(cliPath, currentVsixPath, update.userDataDir, update.extensionsDir);
    const afterUpdate = await listInstalledVersions(cliPath, update.userDataDir, update.extensionsDir);
    assertInstalledVersion(afterUpdate, currentVersion);
    console.log(`Update install verified: ${publisherExtensionId}@${currentVersion}`);

    if (shouldRunActivation && vscodeExecutablePath) {
        const installedDir = resolveActivationExtensionPath(update.extensionsDir, currentVersion);
        await verifyActivation(
            installedDir,
            vscodeExecutablePath,
        );
        console.log('Installed extension activation smoke test passed.');
    } else {
        console.log('Skipping activation smoke test in this environment. Install/update checks passed.');
    }
}

main().catch((error) => {
    console.error('VSIX install smoke test failed:', error);
    process.exit(1);
});
