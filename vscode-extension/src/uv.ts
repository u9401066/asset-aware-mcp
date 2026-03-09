import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export function getUvPaths(
    platform: NodeJS.Platform = process.platform,
    env: NodeJS.ProcessEnv = process.env,
): string[] {
    const pathApi = platform === 'win32' ? path.win32 : path;
    const homeDir = env.HOME || env.USERPROFILE || '';
    const cargoHome = env.CARGO_HOME || pathApi.join(homeDir, '.cargo');
    const localAppData = env.LOCALAPPDATA || pathApi.join(homeDir, 'AppData', 'Local');
    const candidates: string[] = [];

    if (platform === 'win32') {
        candidates.push(
            'uv',
            path.win32.join(localAppData, 'uv', 'bin', 'uv.exe'),
            path.win32.join(homeDir, '.local', 'bin', 'uv.exe'),
            path.win32.join(cargoHome, 'bin', 'uv.exe'),
            path.win32.join(homeDir, 'scoop', 'shims', 'uv.exe'),
            'C:\\ProgramData\\chocolatey\\bin\\uv.exe',
            'C:\\Program Files\\uv\\uv.exe',
        );
    } else {
        const xdgBinHome = env.XDG_BIN_HOME || '';
        candidates.push(
            'uv',
            path.join(homeDir, '.local', 'bin', 'uv'),
            path.join(cargoHome, 'bin', 'uv'),
            xdgBinHome ? path.join(xdgBinHome, 'uv') : '',
            '/usr/bin/uv',
            '/usr/local/bin/uv',
            '/opt/homebrew/bin/uv',
            '/opt/local/bin/uv',
            '/home/linuxbrew/.linuxbrew/bin/uv',
            '/snap/bin/uv',
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

export function getUvxLaunch(uvPath: string): { command: string; args: string[] } {
    if (uvPath === 'uv') {
        return { command: 'uvx', args: [] };
    }

    return { command: uvPath, args: ['tool', 'run'] };
}
