export interface OllamaModelStatus {
    connected: boolean;
    models: string[];
    missingModels: string[];
}

export function getMissingOllamaModels(
    installedModels: string[],
    requiredModels: Array<string | undefined>,
): string[] {
    const installed = new Set(installedModels.map(model => model.trim()).filter(Boolean));
    const required = Array.from(new Set(requiredModels.map(model => model?.trim()).filter(Boolean) as string[]));
    return required.filter(model => !installed.has(model));
}

export function getRequiredOllamaModelsForLightRag(
    ollamaModel: string | undefined,
    embeddingModel: string | undefined,
    enableLightRag: boolean,
): string[] {
    const required = [ollamaModel, enableLightRag ? embeddingModel : undefined];
    return required.map(model => model?.trim()).filter(Boolean) as string[];
}

export async function checkOllamaModels(
    host: string,
    requiredModels: Array<string | undefined>,
    timeoutMs: number = 5000,
): Promise<OllamaModelStatus> {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        const response = await fetch(`${host}/api/tags`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            return { connected: false, models: [], missingModels: [] };
        }

        const data = await response.json() as { models?: { name: string }[] };
        const models = data.models?.map(model => model.name).filter(Boolean) ?? [];
        return {
            connected: true,
            models,
            missingModels: getMissingOllamaModels(models, requiredModels),
        };
    } catch {
        return { connected: false, models: [], missingModels: [] };
    }
}

export function formatOllamaPullCommands(models: string[]): string {
    return models.map(model => `ollama pull ${model}`).join('\n');
}
