// claudeClient.ts
// -----------------------------------------------------------------------------
// A thin, reusable wrapper around the Anthropic SDK so the rest of the codebase
// never has to repeat model IDs or boilerplate.
//
// Why claude-opus-4-8? It is Anthropic's most capable Opus-tier model — the
// right default for copywriting, research, and the "judgement" tasks in this
// project. If you want cheaper/faster output for high-volume, low-stakes jobs
// (e.g. bulk tag generation), swap to "claude-sonnet-4-6" or "claude-haiku-4-5".
// -----------------------------------------------------------------------------

import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

// The SDK automatically reads ANTHROPIC_API_KEY from the environment.
export const claude = new Anthropic();

// Central place to pick the model. Change once, applies everywhere.
export const MODEL = "claude-opus-4-8";

/**
 * Simple one-shot text generation.
 *
 * `adaptive` thinking lets Claude decide how much to reason on its own — ideal
 * for research/strategy. For short, formulaic copy you can leave it off to save
 * tokens; here we keep it on because marketing copy benefits from a little
 * deliberation about angle and audience.
 */
export async function ask(
  prompt: string,
  opts: { system?: string; maxTokens?: number } = {},
): Promise<string> {
  const response = await claude.messages.create({
    model: MODEL,
    max_tokens: opts.maxTokens ?? 4000,
    system: opts.system,
    thinking: { type: "adaptive" },
    messages: [{ role: "user", content: prompt }],
  });

  // response.content is a list of blocks (thinking, text, ...). Pull the text.
  return response.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { text: string }).text)
    .join("\n");
}
