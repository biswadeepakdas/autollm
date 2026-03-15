/**
 * AutoLLM SDK — wraps LLM providers, logs usage, respects Auto mode config.
 *
 * Usage:
 *   import { AutoLLM } from '@autollm/sdk';
 *   const autollm = new AutoLLM({ apiKey: 'allm_...' });
 *   const result = await autollm.call({
 *     feature: 'onboarding_summary',
 *     provider: 'openai',
 *     model: 'gpt-4.1',
 *     messages: [{ role: 'user', content: 'Summarize...' }],
 *   });
 */

export interface AutoLLMConfig {
  apiKey: string;
  backendUrl?: string;
  /** If true, SDK won't throw on backend errors — just calls the LLM directly */
  failOpen?: boolean;
}

export interface CallParams {
  feature: string;
  provider: 'openai' | 'anthropic' | 'gemini' | 'nvidia_nim';
  model: string;
  messages: Array<{ role: string; content: string }>;
  max_tokens?: number;
  temperature?: number;
  /** Pass your own provider API key — SDK does NOT store provider keys */
  providerApiKey: string;
  /** Any additional provider-specific params */
  [key: string]: any;
}

export interface CallResult {
  content: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  was_rerouted: boolean;
  original_model?: string;
  reroute_reason?: string;
}

interface ProjectConfig {
  project_id: string;
  auto_mode_global: boolean;
  features: Record<string, FeatureConfig>;
  plan: { name: string; code: string; auto_mode_enabled: boolean; monthly_request_limit: number };
}

interface FeatureConfig {
  auto_mode: boolean;
  max_tokens_cap: number | null;
  preferred_model: string | null;
  preferred_provider: string | null;
}

export class AutoLLM {
  private apiKey: string;
  private backendUrl: string;
  private failOpen: boolean;
  private config: ProjectConfig | null = null;
  private configFetchedAt: number = 0;
  private CONFIG_TTL_MS = 60_000; // refresh config every 60s

  constructor(opts: AutoLLMConfig) {
    this.apiKey = opts.apiKey;
    this.backendUrl = (opts.backendUrl || 'http://localhost:8000').replace(/\/$/, '');
    this.failOpen = opts.failOpen !== false; // default true
  }

  // ── Public API ──────────────────────────────────────────────────────────

  async call(params: CallParams): Promise<CallResult> {
    const start = Date.now();
    let usedProvider = params.provider;
    let usedModel = params.model;
    let wasRerouted = false;
    let rerouteReason: string | undefined;
    let maxTokens = params.max_tokens;

    // 1. Fetch config (cached)
    try {
      await this.ensureConfig();
    } catch {
      // Config fetch failed — proceed with original params
    }

    // 2. Apply Auto mode if enabled
    if (this.config) {
      const featureConfig = this.config.features[params.feature];
      const autoEnabled =
        this.config.plan.auto_mode_enabled &&
        this.config.auto_mode_global &&
        (featureConfig?.auto_mode ?? false);

      if (autoEnabled && featureConfig) {
        // Apply preferred model/provider override
        if (featureConfig.preferred_model) {
          usedModel = featureConfig.preferred_model;
          usedProvider = (featureConfig.preferred_provider as any) || params.provider;
          wasRerouted = true;
          rerouteReason = `Auto mode: routed to preferred model ${usedModel}`;
        }
        // Apply token cap
        if (featureConfig.max_tokens_cap) {
          maxTokens = Math.min(maxTokens || Infinity, featureConfig.max_tokens_cap);
        }
      }
    }

    // 3. Call the actual LLM provider
    let result: CallResult;
    try {
      result = await this.callProvider({
        ...params,
        provider: usedProvider,
        model: usedModel,
        max_tokens: maxTokens,
      }, start);
      result.was_rerouted = wasRerouted;
      result.original_model = wasRerouted ? params.model : undefined;
      result.reroute_reason = rerouteReason;
    } catch (err: any) {
      // If rerouted call fails, try original model
      if (wasRerouted) {
        result = await this.callProvider(params, start);
        result.was_rerouted = false;
      } else {
        throw err;
      }
    }

    // 4. Log to backend (fire and forget — never block the app)
    this.logToBackend(params.feature, result).catch(() => {});

    return result;
  }

  // ── Provider dispatch ───────────────────────────────────────────────────

  private async callProvider(params: CallParams, startTime: number): Promise<CallResult> {
    switch (params.provider) {
      case 'openai':
        return this.callOpenAI(params, startTime);
      case 'anthropic':
        return this.callAnthropic(params, startTime);
      case 'gemini':
        return this.callGemini(params, startTime);
      case 'nvidia_nim':
        return this.callNvidiaNIM(params, startTime);
      default:
        throw new Error(`Unsupported provider: ${params.provider}`);
    }
  }

  private async callOpenAI(params: CallParams, startTime: number): Promise<CallResult> {
    const { default: OpenAI } = await import('openai');
    const client = new OpenAI({ apiKey: params.providerApiKey });

    const response = await client.chat.completions.create({
      model: params.model,
      messages: params.messages as any,
      max_tokens: params.max_tokens,
      temperature: params.temperature,
    });

    const choice = response.choices[0];
    return {
      content: choice?.message?.content || '',
      provider: params.provider,
      model: params.model,
      prompt_tokens: response.usage?.prompt_tokens || 0,
      completion_tokens: response.usage?.completion_tokens || 0,
      total_tokens: response.usage?.total_tokens || 0,
      latency_ms: Date.now() - startTime,
      was_rerouted: false,
    };
  }

  private async callAnthropic(params: CallParams, startTime: number): Promise<CallResult> {
    // Use fetch directly — Anthropic SDK pattern
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': params.providerApiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: params.model,
        max_tokens: params.max_tokens || 1024,
        messages: params.messages,
      }),
    });

    const data = await response.json() as any;
    return {
      content: data.content?.[0]?.text || '',
      provider: params.provider,
      model: params.model,
      prompt_tokens: data.usage?.input_tokens || 0,
      completion_tokens: data.usage?.output_tokens || 0,
      total_tokens: (data.usage?.input_tokens || 0) + (data.usage?.output_tokens || 0),
      latency_ms: Date.now() - startTime,
      was_rerouted: false,
    };
  }

  private async callGemini(params: CallParams, startTime: number): Promise<CallResult> {
    // Google Gemini API via REST
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${params.model}:generateContent?key=${params.providerApiKey}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: params.messages.map(m => ({
          role: m.role === 'assistant' ? 'model' : m.role,
          parts: [{ text: m.content }],
        })),
        generationConfig: {
          maxOutputTokens: params.max_tokens,
          temperature: params.temperature,
        },
      }),
    });

    const data = await response.json() as any;
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
    const usage = data.usageMetadata || {};
    return {
      content: text,
      provider: params.provider,
      model: params.model,
      prompt_tokens: usage.promptTokenCount || 0,
      completion_tokens: usage.candidatesTokenCount || 0,
      total_tokens: usage.totalTokenCount || 0,
      latency_ms: Date.now() - startTime,
      was_rerouted: false,
    };
  }

  private async callNvidiaNIM(params: CallParams, startTime: number): Promise<CallResult> {
    // NVIDIA NIM uses OpenAI-compatible API
    const { default: OpenAI } = await import('openai');
    const client = new OpenAI({
      apiKey: params.providerApiKey,
      baseURL: 'https://integrate.api.nvidia.com/v1',
    });

    const response = await client.chat.completions.create({
      model: params.model,
      messages: params.messages as any,
      max_tokens: params.max_tokens,
      temperature: params.temperature,
    });

    const choice = response.choices[0];
    return {
      content: choice?.message?.content || '',
      provider: params.provider,
      model: params.model,
      prompt_tokens: response.usage?.prompt_tokens || 0,
      completion_tokens: response.usage?.completion_tokens || 0,
      total_tokens: response.usage?.total_tokens || 0,
      latency_ms: Date.now() - startTime,
      was_rerouted: false,
    };
  }

  // ── Config fetching ─────────────────────────────────────────────────────

  private async ensureConfig(): Promise<void> {
    if (this.config && Date.now() - this.configFetchedAt < this.CONFIG_TTL_MS) {
      return; // cached
    }
    const res = await fetch(`${this.backendUrl}/api/sdk/config`, {
      headers: { 'X-API-Key': this.apiKey },
    });
    if (res.ok) {
      this.config = await res.json() as ProjectConfig;
      this.configFetchedAt = Date.now();
    }
  }

  // ── Logging ─────────────────────────────────────────────────────────────

  private async logToBackend(feature: string, result: CallResult): Promise<void> {
    try {
      const res = await fetch(`${this.backendUrl}/api/sdk/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
        },
        body: JSON.stringify({
          feature,
          provider: result.provider,
          model: result.model,
          prompt_tokens: result.prompt_tokens,
          completion_tokens: result.completion_tokens,
          total_tokens: result.total_tokens,
          latency_ms: result.latency_ms,
          status_code: 200,
          was_rerouted: result.was_rerouted,
          original_model: result.original_model,
          reroute_reason: result.reroute_reason,
        }),
      });

      // Handle limit exceeded gracefully — don't break the app
      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as any;
        if (body.message?.includes('limit')) {
          console.warn(`[AutoLLM] ${body.message}`);
        }
      }
    } catch {
      // Backend down — silently continue
    }
  }
}

export default AutoLLM;
