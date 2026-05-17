import * as assert from 'assert';
import {
    DEFAULT_TORCH_BACKEND,
    formatTerminalCommand,
    getAssetAwareRuntimeProbeArgs,
    getMarkerRuntimeArgs,
    getUvInstallCommand,
    getUvPaths,
    getUvRunArgs,
    getUvxLaunch,
    PREFERRED_RUNTIME_PYTHON,
    RUNTIME_PYTHON_CANDIDATES,
} from '../../uv';

describe('uv path discovery', () => {
    it('includes common Windows install locations', () => {
        const paths = getUvPaths('win32', {
            USERPROFILE: 'C:\\Users\\alice',
            LOCALAPPDATA: 'C:\\Users\\alice\\AppData\\Local',
            CARGO_HOME: 'C:\\Users\\alice\\.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('C:\\Users\\alice\\AppData\\Local\\uv\\bin\\uv.exe'));
        assert.ok(paths.includes('C:\\Users\\alice\\scoop\\shims\\uv.exe'));
        assert.ok(paths.includes('C:\\ProgramData\\chocolatey\\bin\\uv.exe'));
        assert.ok(paths.indexOf('C:\\Users\\alice\\AppData\\Local\\uv\\bin\\uv.exe') < paths.indexOf('uv'));
    });

    it('prefers USERPROFILE over POSIX HOME on Windows', () => {
        const paths = getUvPaths('win32', {
            HOME: '/c/Users/alice',
            USERPROFILE: 'C:\\Users\\alice',
            LOCALAPPDATA: 'C:\\Users\\alice\\AppData\\Local',
        });

        assert.ok(paths.includes('C:\\Users\\alice\\.local\\bin\\uv.exe'));
        assert.ok(!paths.includes('\\c\\Users\\alice\\.local\\bin\\uv.exe'));
    });

    it('includes common Linux install locations', () => {
        const paths = getUvPaths('linux', {
            HOME: '/home/alice',
            CARGO_HOME: '/home/alice/.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('/home/alice/.local/bin/uv'));
        assert.ok(paths.includes('/home/alice/.cargo/bin/uv'));
        assert.ok(paths.includes('/home/linuxbrew/.linuxbrew/bin/uv'));
        assert.ok(paths.includes('/snap/bin/uv'));
        assert.ok(paths.indexOf('/home/alice/.local/bin/uv') < paths.indexOf('uv'));
    });

    it('includes common macOS install locations', () => {
        const paths = getUvPaths('darwin', {
            HOME: '/Users/alice',
            CARGO_HOME: '/Users/alice/.cargo',
        });

        assert.ok(paths.includes('uv'));
        assert.ok(paths.includes('/Users/alice/.local/bin/uv'));
        assert.ok(paths.includes('/opt/homebrew/bin/uv'));
        assert.ok(paths.includes('/opt/local/bin/uv'));
    });

    it('builds uv tool run launch args with preferred python when uv is on PATH', () => {
        const launch = getUvxLaunch('uv');

        assert.strictEqual(launch.command, 'uv');
        assert.deepStrictEqual(launch.args, ['tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('keeps Python 3.10 as a runtime fallback for older macOS machines', () => {
        assert.deepStrictEqual(RUNTIME_PYTHON_CANDIDATES, ['3.11', '3.10']);
    });

    it('builds uv tool run launch args with preferred python', () => {
        const launch = getUvxLaunch('/usr/local/bin/uv');

        assert.strictEqual(launch.command, '/usr/local/bin/uv');
        assert.deepStrictEqual(launch.args, ['tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds uv run args with preferred python', () => {
        assert.deepStrictEqual(getUvRunArgs(), ['run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('does not add the local marker extra while the marker backend is on security hold', () => {
        assert.deepStrictEqual(
            getUvRunArgs(PREFERRED_RUNTIME_PYTHON, true),
            ['run', '--python', PREFERRED_RUNTIME_PYTHON],
        );
    });

    it('does not build marker runtime args while the marker backend is on security hold', () => {
        assert.deepStrictEqual(getMarkerRuntimeArgs(DEFAULT_TORCH_BACKEND), []);
    });

    it('omits marker runtime args from uvx launch while the marker backend is on security hold', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu');

        assert.deepStrictEqual(launch.args, ['tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('pins server version with --from when serverVersion provided', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19');

        assert.deepStrictEqual(launch.args, [
            'tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON, '--from', 'asset-aware-mcp==0.6.19',
        ]);
    });

    it('adds --upgrade flag when upgrade is true', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19', true);

        assert.ok(launch.args.includes('--upgrade'));
        assert.ok(launch.args.includes('--from'));
        assert.ok(launch.args.includes('asset-aware-mcp==0.6.19'));
    });

    it('combines version pin and upgrade without marker args while the marker backend is on security hold', () => {
        const launch = getUvxLaunch('/usr/bin/uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu', '0.5.3', true);

        assert.strictEqual(launch.command, '/usr/bin/uv');
        assert.deepStrictEqual(launch.args, [
            'tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON,
            '--upgrade', '--from', 'asset-aware-mcp==0.5.3',
        ]);
    });

    it('builds a runtime probe command that exits after importing the MCP server', () => {
        const launch = getUvxLaunch('/usr/bin/uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.19');
        const args = getAssetAwareRuntimeProbeArgs(launch.args);

        assert.deepStrictEqual(args.slice(0, launch.args.length), launch.args);
        assert.deepStrictEqual(args.slice(-3, -1), ['python', '-c']);
        assert.ok(args[args.length - 1].includes('src.presentation.server'));
    });

    it('builds a Windows uv installer command that works on older PowerShell defaults', () => {
        const install = getUvInstallCommand('win32');

        assert.strictEqual(install.command, 'powershell.exe');
        assert.ok(install.args.includes('-NoProfile'));
        assert.ok(install.args.includes('-NonInteractive'));
        assert.ok(install.args.includes('-ExecutionPolicy'));
        assert.ok(install.args.includes('Bypass'));
        const script = install.args.join(' ');
        assert.match(script, /Tls12/);
        assert.match(script, /\[Net\.SecurityProtocolType\]3072/);
        assert.match(script, /Invoke-WebRequest/);
        assert.match(script, /Net\.WebClient/);
    });

    it('formats Windows terminal commands with a PowerShell call operator for spaced executables', () => {
        const command = formatTerminalCommand(
            'C:\\Program Files\\uv\\uv.exe',
            ['tool', 'install', '--upgrade', 'asset-aware-mcp[lightrag]==0.6.35'],
            'win32',
        );

        assert.strictEqual(
            command,
            "& 'C:\\Program Files\\uv\\uv.exe' 'tool' 'install' '--upgrade' 'asset-aware-mcp[lightrag]==0.6.35'",
        );
    });

    it('single-quotes Windows terminal commands to avoid PowerShell expansion', () => {
        const command = formatTerminalCommand(
            "C:\\Users\\O'Hara\\uv.exe",
            ['sync', '--extra', 'light rag', 'value$HOME;$(whoami)&'],
            'win32',
        );

        assert.strictEqual(
            command,
            "& 'C:\\Users\\O''Hara\\uv.exe' 'sync' '--extra' 'light rag' 'value$HOME;$(whoami)&'",
        );
    });

    it('quotes POSIX package specs so zsh does not treat extras as globs', () => {
        const command = formatTerminalCommand(
            'uv',
            ['tool', 'install', 'asset-aware-mcp[lightrag]==0.6.35'],
            'darwin',
        );

        assert.strictEqual(command, "uv tool install 'asset-aware-mcp[lightrag]==0.6.35'");
    });
});
