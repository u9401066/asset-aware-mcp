import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export const PREFERRED_RUNTIME_PYTHON = '3.11';
export const FALLBACK_RUNTIME_PYTHONS = ['3.10'] as const;
export const RUNTIME_PYTHON_CANDIDATES = [PREFERRED_RUNTIME_PYTHON, ...FALLBACK_RUNTIME_PYTHONS];
export const RUNTIME_PYTHON_VERSION_KEY = 'assetAwareMcp.runtimePythonVersion';
export const DEFAULT_TORCH_BACKEND = 'cpu';
export const ASSET_AWARE_RUNTIME_PROBE = "import src.presentation.server; print('asset-aware-mcp runtime ready')";
export const MARKER_BACKEND_SECURITY_HOLD_MESSAGE =
    'Marker backend requested but temporarily disabled: marker-pdf pins Pillow<11 while asset-aware-mcp requires Pillow>=12.2.0 for patched image-processing security. Using the secure PyMuPDF runtime until marker-pdf supports patched Pillow.';
const UV_INSTALL_URL = 'https://astral.sh/uv/install.ps1';

export interface UvInstallCommand {
    command: string;
    args: string[];
}

function quotePowerShell(value: string): string {
    return `'${value.replace(/'/g, "''")}'`;
}

function quotePosixShell(value: string): string {
    return `'${value.replace(/'/g, `'\\''`)}'`;
}

function shouldQuotePosix(value: string): boolean {
    return value.length === 0 || /[^A-Za-z0-9_@%+=:,./-]/u.test(value);
}

export function formatTerminalCommand(
    command: string,
    args: string[],
    platform: NodeJS.Platform = process.platform,
): string {
    if (platform === 'win32') {
        const executable = `& ${quotePowerShell(command)}`;
        const quotedArgs = args.map((arg) => quotePowerShell(arg));
        return [executable, ...quotedArgs].join(' ');
    }

    const executable = shouldQuotePosix(command) ? quotePosixShell(command) : command;
    const quotedArgs = args.map((arg) => shouldQuotePosix(arg) ? quotePosixShell(arg) : arg);
    return [executable, ...quotedArgs].join(' ');
}

export function getUvInstallCommand(
    platform: NodeJS.Platform = process.platform,
): UvInstallCommand {
    if (platform === 'win32') {
        const script = [
            "$ProgressPreference = 'SilentlyContinue'",
            "try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor ([Net.SecurityProtocolType]3072) } catch {} }",
            `$url = '${UV_INSTALL_URL}'`,
            "$installer = $null",
            "if (Get-Command Invoke-WebRequest -ErrorAction SilentlyContinue) {",
            "  try { $installer = (Invoke-WebRequest -UseBasicParsing $url).Content } catch {}",
            "}",
            "if (-not $installer) {",
            "  $installer = (New-Object Net.WebClient).DownloadString($url)",
            "}",
            "Invoke-Expression $installer",
        ].join('; ');
        return {
            command: 'powershell.exe',
            args: [
                '-NoProfile',
                '-NonInteractive',
                '-ExecutionPolicy',
                'Bypass',
                '-Command',
                script,
            ],
        };
    }

    return {
        command: 'sh',
        args: ['-c', 'curl -LsSf https://astral.sh/uv/install.sh | sh'],
    };
}

export function getUvPaths(
    platform: NodeJS.Platform = process.platform,
    env: NodeJS.ProcessEnv = process.env,
): string[] {
    const pathApi = platform === 'win32' ? path.win32 : path.posix;
    const homeDir = platform === 'win32'
        ? env.USERPROFILE || env.HOME || ''
        : env.HOME || env.USERPROFILE || '';
    const cargoHome = env.CARGO_HOME || pathApi.join(homeDir, '.cargo');
    const localAppData = env.LOCALAPPDATA || pathApi.join(homeDir, 'AppData', 'Local');
    const candidates: string[] = [];

    if (platform === 'win32') {
        candidates.push(
            path.win32.join(localAppData, 'uv', 'bin', 'uv.exe'),
            path.win32.join(homeDir, '.local', 'bin', 'uv.exe'),
            path.win32.join(cargoHome, 'bin', 'uv.exe'),
            path.win32.join(homeDir, 'scoop', 'shims', 'uv.exe'),
            'C:\\ProgramData\\chocolatey\\bin\\uv.exe',
            'C:\\Program Files\\uv\\uv.exe',
            'uv',
        );
    } else {
        const xdgBinHome = env.XDG_BIN_HOME || '';
        candidates.push(
            pathApi.join(homeDir, '.local', 'bin', 'uv'),
            pathApi.join(cargoHome, 'bin', 'uv'),
            xdgBinHome ? pathApi.join(xdgBinHome, 'uv') : '',
            '/usr/bin/uv',
            '/usr/local/bin/uv',
            '/opt/homebrew/bin/uv',
            '/opt/local/bin/uv',
            '/home/linuxbrew/.linuxbrew/bin/uv',
            '/snap/bin/uv',
            'uv',
        );
    }

    return Array.from(new Set(candidates.filter(Boolean)));
}

export async function findUvPath(): Promise<string | null> {
    for (const uvPath of getUvPaths()) {
        try {
            if (uvPath === 'uv') {
                await execFileAsync('uv', ['--version']);
                return 'uv';
            }

            if (fs.existsSync(uvPath)) {
                await execFileAsync(uvPath, ['--version']);
                return uvPath;
            }
        } catch {
            // Try the next candidate.
        }
    }

    return null;
}

export async function getUvVersion(uvPath: string): Promise<string> {
    const command = uvPath === 'uv' ? 'uv' : uvPath;
    const { stdout } = await execFileAsync(command, ['--version']);
    return stdout.trim();
}

export function getUvRunArgs(
    pythonVersion: string = PREFERRED_RUNTIME_PYTHON,
    _withMarker: boolean = false,
): string[] {
    return ['run', '--python', pythonVersion];
}

export function getMarkerRuntimeArgs(_torchBackend: string = DEFAULT_TORCH_BACKEND): string[] {
    return [];
}

export function getUvxLaunch(
    uvPath: string,
    pythonVersion: string = PREFERRED_RUNTIME_PYTHON,
    withMarker: boolean = false,
    torchBackend: string = DEFAULT_TORCH_BACKEND,
    serverVersion?: string,
    upgrade: boolean = false,
): { command: string; args: string[] } {
    const markerArgs = withMarker ? getMarkerRuntimeArgs(torchBackend) : [];
    const upgradeArgs = upgrade ? ['--upgrade'] : [];
    const fromArgs = serverVersion ? ['--from', `asset-aware-mcp==${serverVersion}`] : [];

    const command = uvPath === 'uv' ? 'uv' : uvPath;
    return {
        command,
        args: ['tool', 'run', '--python', pythonVersion, ...upgradeArgs, ...fromArgs, ...markerArgs],
    };
}

export function getAssetAwareRuntimeProbeArgs(launchArgs: string[]): string[] {
    return [...launchArgs, 'python', '-c', ASSET_AWARE_RUNTIME_PROBE];
}
