<template>
	<div class="scope-selector flex min-h-0 flex-col">
		<header class="border-default flex min-h-10 items-baseline gap-2 border-b px-3 py-2">
			<span :class="SECTION_LABEL" class="shrink-0">Scope</span>
			<span class="text-tertiary text-2xs min-w-0 truncate font-mono">what you are editing</span>
		</header>

		<div class="px-3 pt-3 pb-2">
			<n-input v-model:value="search" size="small" placeholder="Find a customer" clearable>
				<template #prefix><Icon name="carbon:search" :size="14" /></template>
			</n-input>
		</div>

		<!-- The list fills the rail and scrolls inside it, so the editor beside it sets the height. -->
		<div class="relative h-80 min-h-0 lg:h-auto lg:flex-1">
			<n-scrollbar class="absolute! inset-0" data-testid="policy-scopes" trigger="none">
				<div
					ref="tablist"
					class="flex flex-col pb-2"
					role="tablist"
					aria-orientation="vertical"
					aria-label="Policy scope"
					@keydown="onKeydown"
				>
					<template v-for="option of options" :key="option.key">
						<div v-if="option.key === firstCustomerKey" :class="SECTION_LABEL" class="px-3 pt-3 pb-1 text-[10px]!">
							Customers · {{ customerCount }}
						</div>
						<button
							type="button"
							role="tab"
							class="scope-option flex items-center gap-2.5 py-2 pr-2 pl-3 text-left text-sm"
							:class="{ 'is-active': option.code === modelValue }"
							:aria-selected="option.code === modelValue"
							:aria-controls="panelId"
							:tabindex="option.code === modelValue ? 0 : -1"
							:data-testid="`policy-scope-${option.key}`"
							@click="select(option.code)"
						>
							<span class="scope-mark grid size-6 shrink-0 place-items-center rounded-md" aria-hidden="true">
								<Icon v-if="!option.code" name="carbon:earth" :size="14" />
								<span v-else class="font-mono text-[10px] font-semibold">{{ initials(option.label) }}</span>
							</span>
							<span class="flex min-w-0 flex-1 flex-col leading-tight">
								<span class="scope-label truncate">{{ option.label }}</span>
								<span class="text-tertiary text-2xs truncate font-mono">
									{{ option.code ?? "every customer" }}
								</span>
							</span>
							<span class="flex shrink-0 items-center gap-1">
								<n-tooltip v-if="option.code && calendars.has(option.code)">
									<template #trigger>
										<Icon
											name="carbon:calendar"
											:size="13"
											class="text-tertiary"
											:data-testid="`policy-scope-calendar-${option.key}`"
										/>
									</template>
									Has its own business hours
								</n-tooltip>
								<n-tag v-if="option.overrides" size="tiny" type="warning" :bordered="false" round>
									{{ option.overrides }} override{{ option.overrides === 1 ? "" : "s" }}
								</n-tag>
								<Icon name="carbon:chevron-right" :size="14" class="scope-chevron" />
							</span>
						</button>
					</template>
					<p v-if="!customerCount" class="text-tertiary m-0 px-3 py-3 text-xs">No customer matches.</p>
				</div>
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
// The SLA policy scope picker: Global, then every customer, as a vertical tab list.
// It drives the editor panel beside it (aria-controls), and the selected tab takes
// that panel's surface and runs into it, so the pairing reads at a glance. Arrow keys
// move between tabs; Enter or Space opens one (each opening loads a policy).
import { NInput, NScrollbar, NTag, NTooltip } from "naive-ui"
import { computed, nextTick, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"

export interface ScopeOption {
	key: string
	/** null is the global policy. */
	code: string | null
	label: string
	overrides: number
}

const {
	options,
	calendars,
	panelId
} = defineProps<{
	options: ScopeOption[]
	/** Customers with business hours of their own. */
	calendars: Set<string>
	/** The id of the panel these tabs control. */
	panelId: string
}>()

const modelValue = defineModel<string | null>({ required: true })
const search = defineModel<string>("search", { default: "" })

const tablist = useTemplateRef<HTMLElement>("tablist")

const customerCount = computed(() => options.filter(option => option.code).length)
const firstCustomerKey = computed(() => options.find(option => option.code)?.key)

function initials(label: string) {
	const words = label.split(/[\s_-]+/).filter(Boolean)
	return (words.length > 1 ? words[0][0] + words[1][0] : label.slice(0, 2)).toUpperCase()
}

function select(code: string | null) {
	modelValue.value = code
}

/** Roving focus over the tabs: ↑/↓ move, Home/End jump, Enter/Space open. */
async function onKeydown(event: KeyboardEvent) {
	const tabs = [...(tablist.value?.querySelectorAll<HTMLButtonElement>("[role=tab]") ?? [])]
	const current = tabs.indexOf(document.activeElement as HTMLButtonElement)
	if (current < 0) return
	const next =
		event.key === "ArrowDown"
			? Math.min(current + 1, tabs.length - 1)
			: event.key === "ArrowUp"
				? Math.max(current - 1, 0)
				: event.key === "Home"
					? 0
					: event.key === "End"
						? tabs.length - 1
						: -1
	if (next < 0) return
	event.preventDefault()
	await nextTick()
	tabs[next].focus()
}
</script>

<style scoped>
.scope-option {
	position: relative;
	color: var(--fg-secondary-color);
	transition:
		background-color 0.15s,
		color 0.15s;
}

.scope-option:hover {
	background-color: var(--hover-color);
	color: var(--fg-default-color);
}

.scope-option:focus-visible {
	outline: 1px solid var(--primary-color);
	outline-offset: -1px;
}

.scope-mark {
	background-color: var(--hover-color);
	color: var(--fg-secondary-color);
}

.scope-chevron {
	opacity: 0;
	color: var(--primary-color);
	transition: opacity 0.15s;
}

/* The open tab: the editor's surface (the rail is the secondary one) lightly tinted, an accent bar and
   a chevron towards the panel it opened, so tab and panel read as one piece. */
.scope-option.is-active {
	background-color: color-mix(in srgb, var(--primary-color) 7%, var(--bg-default-color));
	color: var(--fg-default-color);
	box-shadow: inset 2px 0 0 var(--primary-color);
}

.scope-option.is-active .scope-label {
	font-weight: 600;
}

.scope-option.is-active .scope-mark {
	background-color: rgb(var(--primary-color-rgb) / 0.16);
	color: var(--primary-color);
}

.scope-option.is-active .scope-chevron {
	opacity: 1;
}
</style>
