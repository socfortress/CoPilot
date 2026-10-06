<template>
	<div class="uba-drawer-header flex min-w-0 flex-col gap-3 py-1" data-testid="uba-drawer-header">
		<div class="flex min-w-0 items-start gap-4">
			<span class="icon-tile grid size-11 shrink-0 place-items-center rounded-lg" aria-hidden="true">
				<Icon :name="meta?.icon ?? 'carbon:user'" :size="20" />
			</span>
			<div class="flex min-w-0 flex-1 flex-col gap-1">
				<span class="text-tertiary font-mono text-[10px] tracking-widest uppercase" data-testid="uba-drawer-kind">
					{{ meta?.kind ?? kind }}
				</span>
				<template v-if="meta">
					<h3 class="m-0 truncate text-lg leading-tight font-semibold" :title="meta.title" data-testid="uba-drawer-title">
						{{ meta.title }}
					</h3>
					<div v-if="meta.key" class="flex min-w-0 items-center gap-1">
						<code class="text-tertiary min-w-0 truncate font-mono text-[11px]">{{ meta.key }}</code>
						<n-button
							quaternary
							size="tiny"
							class="opacity-70"
							:aria-label="`Copy ${meta.keyLabel ?? 'key'}`"
							data-testid="uba-drawer-copy"
							@click="copyKey"
						>
							<template #icon><Icon :name="copied ? 'carbon:checkmark' : 'carbon:copy'" :size="12" /></template>
						</n-button>
					</div>
				</template>
				<template v-else>
					<n-skeleton text class="h-5! w-56" />
					<n-skeleton text class="h-3! w-40" />
				</template>
			</div>
			<RiskMeter v-if="meta?.risk != null" :risk="meta.risk" :threshold="meta.threshold ?? 100" size="lg" />
		</div>
		<div v-if="meta?.tags?.length" class="flex flex-wrap items-center gap-1.5">
			<n-tag
				v-for="tag of meta.tags"
				:key="tag.label"
				size="small"
				:type="tag.type ?? 'default'"
				:bordered="false"
				round
				data-testid="uba-drawer-tag"
			>
				<template v-if="tag.icon" #icon><Icon :name="tag.icon" :size="12" /></template>
				{{ tag.label }}
			</n-tag>
			<slot name="extra" />
		</div>
	</div>
</template>

<script setup lang="ts">
// The header of an entity or alert drawer: what it is (a small mono label), its name, its key (copy
// it), and its risk as the headline figure; badges for what qualifies it underneath. The drawer
// draws the close button beside it. Until the item loads, a skeleton keeps the height.
import { useClipboard } from "@vueuse/core"
import { NButton, NSkeleton, NTag, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import RiskMeter from "./RiskMeter.vue"

export interface UbaDrawerMeta {
	kind: string
	icon: string
	title: string
	key?: string | null
	keyLabel?: string
	risk?: number | null
	threshold?: number
	tags?: { label: string; type?: "default" | "success" | "warning" | "error" | "info"; icon?: string }[]
}

const { meta, kind = "" } = defineProps<{ meta: UbaDrawerMeta | null; kind?: string }>()

const message = useMessage()
const { copy, copied } = useClipboard({ legacy: true })

async function copyKey() {
	if (!meta?.key) return
	await copy(meta.key)
	message.success(`${meta.keyLabel ?? "Key"} copied`)
}
</script>

<style scoped>
.icon-tile {
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.1);
	box-shadow: inset 0 0 0 1px rgb(var(--primary-color-rgb) / 0.25);
}
</style>
