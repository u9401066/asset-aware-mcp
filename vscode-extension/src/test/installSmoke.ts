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
import {
    DEFAULT_MCP_IMAGE_RESPONSE_CHARS,
    DEFAULT_MCP_TEXT_RESPONSE_CHARS,
    DEFAULT_SECTION_TREE_LOAD_MAX_BYTES,
    DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
    DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES,
} from '../defaults';
import {
    DEFAULT_TORCH_BACKEND,
    findUvPath,
    getAssetAwareRuntimeProbeArgs,
    getUvxLaunch,
    PREFERRED_RUNTIME_PYTHON,
} from '../uv';

const execFileAsync = promisify(execFile);

const extensionRoot = path.resolve(__dirname, '../..');
const suitePath = path.resolve(__dirname, './suite/index');
const publisherExtensionId = 'u9401066.asset-aware-mcp';
const packageJson = JSON.parse(
    fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'),
) as { version: string };
const currentVersion = packageJson.version;
const requireActivation = process.argv.includes('--require-activation') ||
    process.env.ASSET_AWARE_MCP_REQUIRE_ACTIVATION === '1';
const verifyRuntimeCommand = process.argv.includes('--verify-runtime-command') ||
    process.env.ASSET_AWARE_MCP_VERIFY_RUNTIME_COMMAND === '1';
type VSCodeQuality = 'stable' | 'insiders';

function parseVSCodeQuality(): VSCodeQuality {
    const inlineArg = process.argv.find((arg) => arg.startsWith('--vscode-quality='));
    const qualityIndex = process.argv.indexOf('--vscode-quality');
    const rawValue = inlineArg?.split('=', 2)[1] ??
        (qualityIndex >= 0 ? process.argv[qualityIndex + 1] : undefined) ??
        process.env.ASSET_AWARE_MCP_VSCODE_QUALITY ??
        'stable';
    if (rawValue === 'stable' || rawValue === 'insiders') {
        return rawValue;
    }
    throw new Error(`Unsupported VS Code quality "${rawValue}". Use "stable" or "insiders".`);
}

async function runCommand(
    command: string,
    args: string[],
    cwd?: string,
    env: NodeJS.ProcessEnv = process.env,
): Promise<string> {
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
            env,
            maxBuffer,
        });

        return `${stdout}${stderr}`.trim();
    }

    const { stdout, stderr } = await execFileAsync(command, args, {
        cwd,
        env,
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

function findAvailableCli(quality: VSCodeQuality): string | null {
    const candidates = process.platform === 'win32'
        ? (quality === 'insiders' ? ['code-insiders.cmd'] : ['code.cmd', 'code-insiders.cmd'])
        : (quality === 'insiders' ? ['code-insiders'] : ['code', 'codium', 'code-insiders']);

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

async function verifyRuntimeDiagnostics(): Promise<void> {
    const uvPath = await findUvPath();
    if (!uvPath) {
        throw new Error('Could not find uv for Asset-Aware MCP runtime diagnostics.');
    }
    const runtimeDirs = createIsolatedDirs('asset-aware-runtime');
    const runtimeDataDir = path.join(runtimeDirs.baseDir, 'data');
    const runtimeLogDir = path.join(runtimeDataDir, 'logs');
    const runtimeCacheDir = path.join(runtimeDataDir, '.uv-cache');
    fs.mkdirSync(runtimeLogDir, { recursive: true });
    fs.mkdirSync(runtimeCacheDir, { recursive: true });
    const runtimeEnv: NodeJS.ProcessEnv = {
        ...process.env,
        DATA_DIR: runtimeDataDir,
        UV_CACHE_DIR: runtimeCacheDir,
        ENABLE_LIGHTRAG: 'false',
        ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS: DEFAULT_MCP_TEXT_RESPONSE_CHARS,
        ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS: DEFAULT_MCP_IMAGE_RESPONSE_CHARS,
        ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES: DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES,
        ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES: DEFAULT_SECTION_TREE_LOAD_MAX_BYTES,
        ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES: DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
        ASSET_AWARE_SUPPRESS_MARKER_OUTPUT: 'true',
        ASSET_AWARE_MARKER_OUTPUT_LOG: path.join(runtimeLogDir, 'marker.log'),
    };

    const launch = getUvxLaunch(
        uvPath,
        PREFERRED_RUNTIME_PYTHON,
        false,
        DEFAULT_TORCH_BACKEND,
        currentVersion,
    );
    const diagnosticArgs = launch.args[0] === 'tool' && launch.args[1] === 'run'
        ? ['tool', 'run', '--isolated', ...launch.args.slice(2)]
        : ['--isolated', ...launch.args];
    const probeOutput = await runCommand(
        launch.command,
        getAssetAwareRuntimeProbeArgs(diagnosticArgs),
        extensionRoot,
        runtimeEnv,
    );
    if (!probeOutput.includes('asset-aware-mcp runtime ready')) {
        throw new Error(`Runtime import probe did not report readiness: ${probeOutput}`);
    }

    const helpOutput = await runCommand(
        launch.command,
        [...diagnosticArgs, 'asset-aware-mcp', '--help'],
        extensionRoot,
        runtimeEnv,
    );
    if (!helpOutput.includes('doctor') || !helpOutput.includes('list-tools')) {
        throw new Error(`Runtime --help did not expose diagnostics commands: ${helpOutput}`);
    }

    const doctorOutput = await runCommand(
        launch.command,
        [...diagnosticArgs, 'asset-aware-mcp', 'doctor', '--json'],
        extensionRoot,
        runtimeEnv,
    );
    if (!doctorOutput.includes('"package"') || !doctorOutput.includes('"runtime"')) {
        throw new Error(`Runtime doctor did not return diagnostics JSON: ${doctorOutput}`);
    }

    const toolsOutput = await runCommand(
        launch.command,
        [...diagnosticArgs, 'asset-aware-mcp', 'list-tools', '--json'],
        extensionRoot,
        runtimeEnv,
    );
    if (!toolsOutput.includes('list_documents') || !toolsOutput.includes('knowledge')) {
        throw new Error(`Runtime list-tools did not expose core MCP tools: ${toolsOutput}`);
    }
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

    throw new Error(
        `Could not locate installed extension under ${extensionsDir}. ` +
        `Entries: ${entries.length > 0 ? entries.join(', ') : '(empty)'}`,
    );
}

async function verifyActivation(
    isolatedDirs: { baseDir: string; userDataDir: string; extensionsDir: string; workspaceDir: string },
    vscodeExecutablePath: string,
): Promise<void> {
    const installedExtensionDir = resolveActivationExtensionPath(isolatedDirs.extensionsDir, currentVersion);
    const previousElectronRunAsNode = process.env.ELECTRON_RUN_AS_NODE;
    delete process.env.ELECTRON_RUN_AS_NODE;
    try {
        await runTests({
            vscodeExecutablePath,
            extensionDevelopmentPath: installedExtensionDir,
            extensionTestsPath: suitePath,
            extensionTestsEnv: {
                ...process.env,
                ASSET_AWARE_MCP_VERIFY_PROVIDER_LAUNCH: '1',
                ASSET_AWARE_MCP_EXPECT_INSTALLED_EXTENSION: '1',
                ASSET_AWARE_MCP_EXPECT_EXTENSION_DIR: installedExtensionDir,
            },
            launchArgs: [],
        });
    } finally {
        if (previousElectronRunAsNode === undefined) {
            delete process.env.ELECTRON_RUN_AS_NODE;
        } else {
            process.env.ELECTRON_RUN_AS_NODE = previousElectronRunAsNode;
        }
    }
}

async function main(): Promise<void> {
    const needsHeadlessDisplay = process.platform === 'linux' && !process.env.DISPLAY && !process.env.WAYLAND_DISPLAY;
    if (requireActivation && needsHeadlessDisplay) {
        throw new Error('Activation smoke requires DISPLAY/WAYLAND_DISPLAY on Linux. Run with xvfb-run or a desktop session.');
    }

    const shouldRunActivation = requireActivation ||
        (process.platform !== 'win32' && (!needsHeadlessDisplay || Boolean(process.env.CI)));
    const currentVsixPath = await packageCurrentVsix();
    const oldVsixPath = path.join(extensionRoot, 'asset-aware-mcp-0.2.10.vsix');
    const vscodeQuality = parseVSCodeQuality();
    console.log(`VS Code quality for install smoke: ${vscodeQuality}`);

    if (verifyRuntimeCommand) {
        await verifyRuntimeDiagnostics();
        console.log('Asset-Aware MCP runtime diagnostics command smoke test passed.');
    } else {
        console.log(
            'Skipping runtime diagnostics command smoke test. ' +
            'Set ASSET_AWARE_MCP_VERIFY_RUNTIME_COMMAND=1 to require runtime import and --help checks.',
        );
    }

    let vscodeExecutablePath: string | undefined;
    const localCliPath = findAvailableCli(vscodeQuality);
    let cliPath = localCliPath;

    if (
        !cliPath ||
        shouldRunActivation ||
        (process.platform === 'win32' && vscodeQuality === 'stable')
    ) {
        vscodeExecutablePath = await downloadAndUnzipVSCode(vscodeQuality);
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
        await verifyActivation(update, vscodeExecutablePath);
        console.log('Installed extension activation smoke test passed.');
    } else {
        console.log(
            'Skipping activation smoke test in this environment. ' +
            'Install/update checks passed; run with xvfb-run or --require-activation to require activation.',
        );
    }
}

main().catch((error) => {
    console.error('VSIX install smoke test failed:', error);
    process.exit(1);
});
