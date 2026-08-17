export interface FencedCodeBlock {
  language: string;
  code: string;
}

export function fencedMarkdown(language: string, code: string): string {
  return `\`\`\`${language}\n${code}\n\`\`\``;
}

export function extractFencedCode(markdown: string): FencedCodeBlock[] {
  const blocks: FencedCodeBlock[] = [];
  const fencePattern = /^```([^\n`]*)\n([\s\S]*?)\n```$/gm;
  let match: RegExpExecArray | null;
  while ((match = fencePattern.exec(markdown)) !== null) {
    blocks.push({
      language: match[1].trim(),
      code: match[2]
    });
  }
  return blocks;
}
