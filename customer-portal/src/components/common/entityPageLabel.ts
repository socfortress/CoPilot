import { i18nGlobal } from "@/lang"

const KNOWN = ["alert", "case", "agent"] as const
type KnownEntity = (typeof KNOWN)[number]

/**
 * "Open alert page" for the button that leaves a modal for the entity's own page (#1310). The
 * callers name the entity by its English noun ("alert", "case", "agent"), read as a key: each has
 * a whole translated sentence, since the noun cannot be slotted into every language's phrase.
 */
export function entityPageLabel(entity: string): string {
	return (KNOWN as readonly string[]).includes(entity)
		? i18nGlobal.t(`common.entityDetails.openPage.${entity as KnownEntity}`)
		: i18nGlobal.t("common.entityDetails.openPage.other", { entity })
}
