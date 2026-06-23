// generateAdCopy.ts
// -----------------------------------------------------------------------------
// Workflow: product idea/description  →  Claude writes a set of ad variants
// (headlines + primary text + a visual brief you hand to Higgsfield).
//
// Run:  npm run adcopy -- "Adjustable laptop stand, aluminium, foldable"
//
// The "visualBrief" field is the bridge to Higgsfield: paste it into the
// Higgsfield Marketing Studio (or its MCP `generate_image`/`generate_video`)
// as the prompt for the creative.
// -----------------------------------------------------------------------------

import { z } from "zod";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { claude, MODEL } from "./claudeClient.js";

const AdSchema = z.object({
  variants: z
    .array(
      z.object({
        angle: z.string().describe("The persuasion angle, e.g. 'posture relief'"),
        headline: z.string().describe("<40 chars, scroll-stopping"),
        primaryText: z.string().describe("Meta primary text, <125 chars ideal"),
        visualBrief: z
          .string()
          .describe(
            "A detailed prompt for an AI image/video tool (Higgsfield): scene, " +
              "subject, lighting, mood, aspect ratio. No text overlays.",
          ),
      }),
    )
    .describe("3 distinct ad variants for A/B testing"),
});

const SYSTEM = `You are a performance-marketing creative strategist for UK/EU paid social.
Produce ad concepts that comply with Meta/TikTok ad policies and UK ASA rules:
- No before/after health claims, no "guaranteed results", no fear-based health framing.
- No prohibited or restricted product claims.
- Each variant must use a genuinely different angle (not reworded duplicates).
Write in British English.`;

export async function generateAdCopy(idea: string) {
  const response = await claude.messages.parse({
    model: MODEL,
    max_tokens: 3000,
    system: SYSTEM,
    thinking: { type: "adaptive" },
    messages: [
      {
        role: "user",
        content: `Create 3 paid-social ad variants for:\n\n"${idea}"`,
      },
    ],
    output_config: { format: zodOutputFormat(AdSchema) },
  });

  if (!response.parsed_output) throw new Error("No ad copy returned.");
  return response.parsed_output.variants;
}

// --- CLI entrypoint ---------------------------------------------------------
const idea = process.argv.slice(2).join(" ");
if (!idea) {
  console.error('Usage: npm run adcopy -- "your product idea"');
  process.exit(1);
}

const variants = await generateAdCopy(idea);
console.log(JSON.stringify(variants, null, 2));
console.log(
  "\n👉 Take each `visualBrief` into Higgsfield (Marketing Studio / generate_image" +
    " / generate_video) to produce the matching creative.",
);
