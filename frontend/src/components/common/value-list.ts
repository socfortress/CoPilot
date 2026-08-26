/** One styled chunk of a ValueList row. */
export interface ValueListPart {
	text: string
	/**
	 * strong — the name you recognise the row by;
	 * accent — what kind of thing it is;
	 * muted  — the identifier you copy out (hash, id), long and quiet.
	 */
	tone?: ValueListTone
}

export type ValueListTone = "strong" | "accent" | "muted"

export type ValueListItem = string | ValueListPart[]

/** Drop empty parts so optional fields don't fight `ValueListPart.text: string`. */
export function valueListParts(chunks: { text?: string; tone?: ValueListTone }[]): ValueListPart[] {
	return chunks.flatMap(({ text, tone }) => (text ? [{ text, tone }] : []))
}

export const PART_TONE: Record<ValueListTone, string> = {
	strong: "text-default font-medium",
	accent: "text-primary",
	muted: "text-tertiary"
}
