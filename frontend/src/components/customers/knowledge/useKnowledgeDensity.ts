import { ref, watch } from "vue"

/** How the Knowledge pane lists its facts: each in its own card, or one row each. */
export type KnowledgeDensity = "large" | "compact"

export const KNOWLEDGE_DENSITY_KEY = "copilot.customer.knowledge.density"

function readDensity(): KnowledgeDensity {
	try {
		return localStorage.getItem(KNOWLEDGE_DENSITY_KEY) === "compact" ? "compact" : "large"
	} catch {
		return "large"
	}
}

/**
 * The viewer's choice of density, for this browser. localStorage only: a private window or
 * blocked storage just starts from the large cards.
 */
export function useKnowledgeDensity() {
	const density = ref<KnowledgeDensity>(readDensity())

	watch(density, value => {
		try {
			localStorage.setItem(KNOWLEDGE_DENSITY_KEY, value)
		} catch {
			// Storage refused: the choice lasts for this page only.
		}
	})

	return { density }
}
