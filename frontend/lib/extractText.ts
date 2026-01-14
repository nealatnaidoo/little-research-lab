import { ContentBlockModel } from "@/lib/api"

/**
 * Extract plain text from content blocks for TTS.
 * Recursively extracts text from TipTap JSON structure.
 */
export function extractTextFromBlocks(blocks: ContentBlockModel[] | undefined): string {
  if (!blocks || blocks.length === 0) return ""

  const textParts: string[] = []

  for (const block of blocks) {
    // Handle markdown blocks with TipTap JSON
    if (block.block_type === ContentBlockModel.block_type.MARKDOWN && block.data_json?.tiptap) {
      const text = extractTextFromTipTap(block.data_json.tiptap)
      if (text) textParts.push(text)
    } else if (block.block_type === ContentBlockModel.block_type.MARKDOWN && block.data_json?.text) {
      // Legacy text format - strip HTML tags
      const text = stripHtml(block.data_json.text)
      if (text) textParts.push(text)
    } else if (block.block_type === ContentBlockModel.block_type.IMAGE && block.data_json?.caption) {
      // Include image captions
      textParts.push(`Image: ${block.data_json.caption}`)
    }
  }

  return textParts.join("\n\n")
}

/**
 * Strip HTML tags from text.
 */
function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()
}

/**
 * Extract plain text from TipTap JSON node.
 */
function extractTextFromTipTap(node: unknown): string {
  if (!node || typeof node !== "object") return ""

  const n = node as Record<string, unknown>

  // If it's a text node, return the text
  if (n.type === "text" && typeof n.text === "string") {
    return n.text
  }

  // If it has content array, recursively extract
  if (Array.isArray(n.content)) {
    const parts = n.content.map(extractTextFromTipTap).filter(Boolean)

    // Add spacing based on block type
    if (n.type === "paragraph" || n.type === "heading") {
      return parts.join("") + "\n"
    }
    if (n.type === "bulletList" || n.type === "orderedList") {
      return parts.join("\n")
    }
    if (n.type === "listItem") {
      return "• " + parts.join("")
    }

    return parts.join("")
  }

  return ""
}
