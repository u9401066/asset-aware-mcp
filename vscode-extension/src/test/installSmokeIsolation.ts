import * as fs from 'fs';
import * as path from 'path';

export async function supportsIsolatedInstall(
    cliPath: string,
    readHelp: (cliPath: string) => Promise<string>,
): Promise<boolean> {
    try {
        // Remote terminal launchers forward extension commands to the live server
        // and can ignore both isolation flags while still returning exit code 0.
        const resolved = fs.realpathSync(cliPath);
        if ([cliPath, resolved].some((value) => /(?:^|[\\/])remote-cli(?:[\\/]|$)/i.test(value))) {
            return false;
        }
        const help = await readHelp(cliPath);
        return ['user-data-dir', 'extensions-dir'].every((flag) =>
            new RegExp(`(?:^|\\s)--${flag}(?=[\\s=<]|$)`, 'm').test(help),
        );
    } catch {
        return false;
    }
}

export function isolatedExtensionDirectory(
    extensionsDir: string,
    extensionId: string,
    version: string,
): string {
    const matches = fs.readdirSync(extensionsDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && entry.name.startsWith(`${extensionId}-`))
        .map((entry) => path.join(extensionsDir, entry.name))
        .filter((directory) => {
            const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8'));
            return `${manifest.publisher}.${manifest.name}` === extensionId && manifest.version === version;
        });
    if (matches.length !== 1) {
        throw new Error(`Expected one isolated ${extensionId}@${version} installation in ${extensionsDir}; found ${matches.length}. CLI output alone is not installation evidence.`);
    }
    return matches[0];
}

export function verifyInstalledAssistantAssets(installedRoot: string, extensionRoot: string): void {
    const assetRoot = path.join('resources', 'repo-assets', 'asset-aware');
    for (const relative of [
        'AGENTS.md',
        '.github/copilot-instructions.md',
        '.github/agents/asset-aware-document.agent.md',
        '.codex/skills/asset-aware-mcp-harness/SKILL.md',
        '.cline/skills/asset-aware-mcp-harness/SKILL.md',
    ]) {
        const expected = fs.readFileSync(path.join(extensionRoot, assetRoot, relative));
        const actual = fs.readFileSync(path.join(installedRoot, assetRoot, relative));
        if (!actual.equals(expected)) {
            throw new Error(`Installed assistant asset differs from the current package source: ${relative}`);
        }
    }
}
