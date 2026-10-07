<template>
	<div class="flex min-w-0 flex-col gap-2" data-testid="identity-card">
		<span v-if="caption" class="text-tertiary font-mono text-[10px] tracking-widest uppercase">{{ caption }}</span>
		<div class="flex min-w-0 items-center gap-2.5">
			<span class="entity-icon" aria-hidden="true">
				<Icon :name="identityKindIcon(kind)" :size="14" />
			</span>
			<div class="flex min-w-0 flex-col">
				<div class="flex min-w-0 items-center gap-1.5">
					<span class="truncate font-semibold" :title="name" data-testid="identity-card-name">
						{{ name }}
					</span>
					<n-tag v-if="identity.privileged" size="tiny" type="warning" :bordered="false">admin</n-tag>
				</div>
				<span class="text-secondary flex flex-wrap items-center gap-x-1.5 font-mono text-[11px] tabular-nums">
					<span v-if="kind">{{ kind }}</span>
					<span v-if="kind" class="text-tertiary">·</span>
					<span
						:class="identity.findings ? 'text-default' : 'text-tertiary'"
						data-testid="identity-card-findings"
					>
						{{ identity.findings }} finding{{ identity.findings === 1 ? "" : "s" }} · 14d
					</span>
					<template v-if="identity.last_seen">
						<span class="text-tertiary">·</span>
						<span :title="String(formatDate(identity.last_seen, dFormats.datetime))">
							seen {{ dayjs(identity.last_seen).fromNow() }}
						</span>
					</template>
					<template v-for="tag of identity.tags" :key="tag">
						<span class="text-tertiary">·</span>
						<span>{{ tag }}</span>
					</template>
				</span>
			</div>
		</div>
		<ul v-if="aliases.length" class="m-0 flex list-none flex-col gap-1 p-0" data-testid="identity-card-aliases">
			<li
				v-for="a of aliases"
				:key="a.raw"
				class="alias flex min-w-0 items-center gap-1.5"
				:class="{ 'is-shared': a.raw === sharedAlias }"
			>
				<span v-if="a.type" class="alias-type shrink-0 font-mono text-[10px]">{{ a.type }}</span>
				<span class="truncate font-mono text-[11px]" :title="a.value">{{ a.value }}</span>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
// One UBA identity in a review row: a kind icon, its name with an admin tag, a mono line of facts
// (kind, findings in the last 14 days, last seen, tags), then its aliases as type + value. The alias
// two identities both claim is highlighted, since that is the reason they are shown together.
import type { UbaIdentitySummary } from "@/types/uba"
import { NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { identityKind, identityKindIcon, identityLabel, splitAlias } from "../utils"

const {
	identity,
	caption,
	sharedAlias,
	maxAliases = 3
} = defineProps<{
	identity: UbaIdentitySummary
	caption?: string
	/** The alias that links this identity to another one: shown first and highlighted. */
	sharedAlias?: string
	maxAliases?: number
}>()

const dFormats = useSettingsStore().dateFormat
const name = computed(() => identityLabel(identity))
const kind = computed(() => identityKind(identity))
const aliases = computed(() => {
	const ordered =
		sharedAlias && identity.aliases.includes(sharedAlias)
			? [sharedAlias, ...identity.aliases.filter(a => a !== sharedAlias)]
			: identity.aliases
	return ordered.slice(0, maxAliases).map(raw => ({ raw, ...splitAlias(raw) }))
})
</script>

<style scoped>
.alias-type {
	padding: 0 5px;
	border-radius: 4px;
	line-height: 1.6;
	color: var(--fg-secondary-color);
	background-color: var(--hover-color);
}

.alias {
	color: var(--fg-secondary-color);
}

.alias.is-shared {
	color: var(--primary-color);
}

.alias.is-shared .alias-type {
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.12);
}
</style>
