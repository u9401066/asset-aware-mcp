import * as assert from 'assert';
import {
    DEFAULT_TORCH_BACKEND,
    getMarkerRuntimeArgs,
    getUvPaths,
    getUvRunArgs,
    getUvxLaunch,
    PREFERRED_RUNTIME_PYTHON,
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

    it('builds uvx launch args with preferred python', () => {
        const launch = getUvxLaunch('uv');

        assert.strictEqual(launch.command, 'uvx');
        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds uv tool run launch args with preferred python', () => {
        const launch = getUvxLaunch('/usr/local/bin/uv');

        assert.strictEqual(launch.command, '/usr/local/bin/uv');
        assert.deepStrictEqual(launch.args, ['tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds uv run args with preferred python', () => {
        assert.deepStrictEqual(getUvRunArgs(), ['run', '--python', PREFERRED_RUNTIME_PYTHON]);
    });

    it('builds marker runtime args with cpu backend by default', () => {
        assert.deepStrictEqual(getMarkerRuntimeArgs(), ['--with', 'marker-pdf', '--torch-backend', DEFAULT_TORCH_BACKEND]);
    });

    it('builds uvx launch args with optional marker backend', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu');

        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON, '--with', 'marker-pdf', '--torch-backend', 'cpu']);
    });

    it('pins server version with --from when serverVersion provided', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.12');

        assert.deepStrictEqual(launch.args, ['--python', PREFERRED_RUNTIME_PYTHON, '--from', 'asset-aware-mcp==0.6.12']);
    });

    it('adds --upgrade flag when upgrade is true', () => {
        const launch = getUvxLaunch('uv', PREFERRED_RUNTIME_PYTHON, false, 'cpu', '0.6.12', true);

        assert.ok(launch.args.includes('--upgrade'));
        assert.ok(launch.args.includes('--from'));
        assert.ok(launch.args.includes('asset-aware-mcp==0.6.12'));
    });

    it('combines version pin, upgrade, and marker args', () => {
        const launch = getUvxLaunch('/usr/bin/uv', PREFERRED_RUNTIME_PYTHON, true, 'cpu', '0.5.3', true);

        assert.strictEqual(launch.command, '/usr/bin/uv');
        assert.deepStrictEqual(launch.args, [
            'tool', 'run', '--python', PREFERRED_RUNTIME_PYTHON,
            '--upgrade', '--from', 'asset-aware-mcp==0.5.3',
            '--with', 'marker-pdf', '--torch-backend', 'cpu',
        ]);
    });
});
