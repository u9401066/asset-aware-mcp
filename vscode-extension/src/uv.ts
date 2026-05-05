import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export const PREFERRED_RUNTIME_PYTHON = '3.11';
export const DEFAULT_TORCH_BACKEND = 'cpu';
export const ASSET_AWARE_RUNTIME_PROBE = "import src.presentation.server; print('asset-aware-mcp runtime ready')";

export function getUvPaths(
    platform: NodeJS.Platform = process.platform,
    env: NodeJS.ProcessEnv = process.env,
): string[] {
    const pathApi = platform === 'win32' ? path.win32 : path.posix;
    const homeDir = env.HOME || env.USERPROFILE || '';
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
    withMarker: boolean = false,
): string[] {
    const markerArgs = withMarker ? ['--extra', 'marker'] : [];
    return ['run', '--python', pythonVersion, ...markerArgs];
}

export function getMarkerRuntimeArgs(torchBackend: string = DEFAULT_TORCH_BACKEND): string[] {
    return ['--with', 'marker-pdf', '--torch-backend', torchBackend];
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

    if (uvPath === 'uv') {
        return { command: 'uvx', args: ['--python', pythonVersion, ...upgradeArgs, ...fromArgs, ...markerArgs] };
    }

    return { command: uvPath, args: ['tool', 'run', '--python', pythonVersion, ...upgradeArgs, ...fromArgs, ...markerArgs] };
}

export function getAssetAwareRuntimeProbeArgs(launchArgs: string[]): string[] {
    return [...launchArgs, 'python', '-c', ASSET_AWARE_RUNTIME_PROBE];
}
