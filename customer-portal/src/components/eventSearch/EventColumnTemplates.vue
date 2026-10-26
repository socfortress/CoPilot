<template>
	<n-popover
		v-model:show="open"
		trigger="click"
		placement="bottom-end"
		:show-arrow="false"
		class="p-0!"
		@update:show="onShow"
	>
		<template #trigger>
			<n-button size="small" secondary :disabled :loading="busy" data-testid="column-layouts-toggle">
				<template #icon><Icon name="carbon:data-table" /></template>
				<span class="text-tertiary mr-1">{{ $t("eventSearch.layouts.toggle") }}</span>
				<span class="max-w-40 truncate" data-testid="column-layouts-current">{{ activeName }}</span>
			</n-button>
		</template>

		<div class="@container w-[min(94vw,44rem)]" data-testid="column-layouts">
			<div class="grid @xl:grid-cols-[16rem_minmax(0,1fr)]">
				<section class="border-default flex min-w-0 flex-col @max-xl:border-b @xl:border-r">
					<header class="bg-secondary border-default flex items-baseline justify-between border-b px-3 py-2">
						<span :class="HEAD">{{ $t("eventSearch.layouts.title") }}</span>
						<span class="text-tertiary font-mono text-xs tabular-nums">{{ templates.length + 1 }}</span>
					</header>
					<div class="divide-border flex max-h-[min(50vh,22rem)] flex-col divide-y overflow-y-auto">
						<div
							v-for="option of options"
							:key="option.key"
							class="group flex min-h-15 min-w-0 items-stretch"
							:class="{ 'bg-secondary/50': previewKey === option.key }"
							data-testid="column-layout-row"
						>
							<TemplateDeleteConfirm
								v-if="option.template && confirmingId === option.template.id"
								:name="option.name"
								:loading="deletingId === option.template.id"
								@confirm="emit('delete', option.template.id)"
								@cancel="confirmingId = null"
							/>
							<template v-else>
								<button
									type="button"
									class="hover:bg-secondary/50 focus-visible:bg-secondary/50 flex min-w-0 grow cursor-pointer items-start gap-2 py-2 pl-3 text-left outline-none"
									:class="option.template ? 'pr-1' : 'pr-3'"
									:data-active="option.key === activeKey"
									data-testid="column-layout"
									@mouseenter="previewKey = option.key"
									@focus="previewKey = option.key"
									@click="apply(option)"
								>
									<Icon
										:name="option.key === activeKey ? 'carbon:checkmark' : 'carbon:dot-mark'"
										:size="14"
										class="mt-0.5 shrink-0"
										:class="option.key === activeKey ? 'text-primary' : 'text-tertiary opacity-40'"
									/>
									<span class="flex min-w-0 grow flex-col gap-0.5">
										<span
											class="text-default truncate text-sm"
											:class="{ 'font-medium': option.key === activeKey }"
										>
											{{ option.name }}
										</span>
										<span class="text-tertiary truncate text-xs">
											{{ summary(option.columns) }}
										</span>
									</span>
								</button>
								<n-button
									v-if="option.template"
									size="tiny"
									quaternary
									type="error"
									class="mr-2 self-center opacity-50 group-hover:opacity-100 focus-visible:opacity-100"
									:aria-label="$t('eventSearch.layouts.deleteTemplate', { name: option.name })"
									data-testid="column-layout-delete"
									@mouseenter="previewKey = option.key"
									@click="confirmingId = option.template.id"
								>
									<template #icon><Icon name="carbon:trash-can" :size="14" /></template>
								</n-button>
							</template>
						</div>
					</div>
					<p v-if="!templates.length" class="text-tertiary border-default m-0 border-t px-3 py-2 text-xs">
						{{ $t("eventSearch.layouts.noTemplates") }}
					</p>
					<footer class="border-default border-t px-3 py-2">
						<n-button text size="tiny" data-testid="column-layouts-manage" @click="manage">
							<template #icon><Icon name="carbon:settings-adjust" :size="14" /></template>
							{{ $t("eventSearch.layouts.manage") }}
						</n-button>
					</footer>
				</section>

				<div class="min-w-0 p-3">
					<EventColumnsPreview
						v-if="previewed"
						:title="previewed.name"
						:columns="previewed.columns"
						:time-field
					/>
				</div>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { EventColumn } from "./eventColumns"
import type { DisplayColumn, EventSearchColumnTemplate } from "@/types/siem"
import { NButton, NPopover } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Icon from "@/components/common/Icon.vue"
import EventColumnsPreview from "./EventColumnsPreview.vue"
import TemplateDeleteConfirm from "./TemplateDeleteConfirm.vue"

/**
 * Switches event search between column layouts (#1258): the source's own, and the user's
 * templates for it. Each one is previewed (every column, its header and field) before it is
 * picked; picking one applies it at once. A template can be deleted here too, once confirmed.
 */

interface LayoutOption {
	key: string
	name: string
	columns: EventColumn[]
	template: EventSearchColumnTemplate | null
}

const {
	templates,
	activeKey,
	sourceName,
	sourceColumns,
	resolve,
	timeField,
	disabled = false,
	busy = false,
	deletingId = null
} = defineProps<{
	templates: EventSearchColumnTemplate[]
	/** "source", a template's id, or null when the columns on screen match no layout. */
	activeKey: string | null
	/** What the source's own layout is called: the SOC's, or the default one. */
	sourceName: string
	sourceColumns: EventColumn[]
	/** A template's columns as the table would show them. */
	resolve: (columns: DisplayColumn[]) => EventColumn[]
	timeField?: string | null
	disabled?: boolean
	busy?: boolean
	/** The template being deleted, while it is. */
	deletingId?: number | null
}>()

const emit = defineEmits<{
	(e: "apply", value: EventSearchColumnTemplate | null): void
	(e: "delete", id: number): void
	(e: "manage"): void
}>()

const HEAD = "text-tertiary text-xxs font-medium tracking-[0.12em] uppercase"
const { t } = useI18n()
const open = ref(false)
const previewKey = ref<string | null>(null)
/** The template whose deletion is being confirmed. */
const confirmingId = ref<number | null>(null)

const options = computed<LayoutOption[]>(() => [
	{ key: "source", name: sourceName, columns: sourceColumns, template: null },
	...templates.map(template => ({
		key: String(template.id),
		name: template.name,
		columns: resolve(template.columns),
		template
	}))
])

const activeName = computed(() => options.value.find(option => option.key === activeKey)?.name ?? t("eventSearch.layouts.custom"))
const previewed = computed(
	() =>
		options.value.find(option => option.key === previewKey.value) ??
		options.value.find(option => option.key === activeKey) ??
		options.value[0]
)

function summary(columns: EventColumn[]): string {
	const labels = columns.slice(0, 3).map(column => column.label)
	return columns.length > 3 ? `${labels.join(" · ")} · +${columns.length - 3}` : labels.join(" · ")
}

function onShow(show: boolean) {
	// Opening shows the layout in force; hovering or focusing another shows that one.
	if (show) previewKey.value = activeKey
	// A confirmation left open never survives the menu closing.
	confirmingId.value = null
}

// Once deleted, the template leaves the list: nothing is left to confirm or preview.
watch(
	() => templates,
	list => {
		if (confirmingId.value !== null && !list.some(template => template.id === confirmingId.value)) {
			confirmingId.value = null
			previewKey.value = activeKey
		}
	}
)

function apply(option: LayoutOption) {
	open.value = false
	if (option.key !== activeKey) emit("apply", option.template)
}

function manage() {
	open.value = false
	emit("manage")
}
</script>
