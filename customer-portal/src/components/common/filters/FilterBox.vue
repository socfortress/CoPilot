<template>
	<n-spin :show="loading" content-class="flex h-full flex-col overflow-hidden">
		<n-card
			class="w-80 min-w-70 grow overflow-hidden"
			size="small"
			content-class="overflow-hidden p-0!"
			header-class="px-3.5! pt-2! pb-2!"
			:embedded
		>
			<template #header>
				<div class="flex items-center justify-between gap-2">
					<span class="text-sm">{{ label || "Filter" }}</span>
					<div class="flex items-center justify-end gap-3">
						<n-popover v-if="options?.length" class="p-0!">
							<template #trigger>
								<n-badge
									dot
									:offset="[-1, 2]"
									:show="!!optionsFilterModel"
									class="[&_.n-badge-sup]:h-1! [&_.n-badge-sup]:w-1! [&_.n-badge-sup]:min-w-1!"
									color="var(--primary-color)"
								>
									<n-button size="small" text :focusable="false">
										<Icon
											name="carbon:search"
											:class="optionsFilterModel ? 'text-primary' : undefined"
										/>
									</n-button>
								</n-badge>
							</template>
							<n-input
								v-model:value="optionsFilterModel"
								size="small"
								clearable
								placeholder="Search option..."
							/>
						</n-popover>
						<n-tooltip class="px-1.5! pt-0! pb-0.5!">
							<template #trigger>
								<n-button size="small" text :focusable="false" @click="clearFilter()">
									<Icon name="carbon:close-outline" />
								</n-button>
							</template>
							<span class="text-xs">Clear filter</span>
						</n-tooltip>
					</div>
				</div>
			</template>
			<n-scrollbar trigger="none">
				<div class="flex flex-col gap-1 px-3 pb-3">
					<div v-if="!options?.length || textInputFallback">
						<n-input
							v-model:value="textInputModel"
							size="small"
							:class="{ 'bg-primary/15!': !!textInputModel }"
							clearable
							:placeholder="placeholder || 'Search by text...'"
							@update:value="setModel()"
						/>
					</div>
					<n-button
						v-for="item of allOptions"
						:key="item.option.value + item.option.label"
						icon-placement="right"
						class="[&_.n-button\_\_content]:grow"
						:class="{ 'opacity-25': item.isMuted }"
						secondary
						:focusable="false"
						size="small"
						:type="isActive(item.option.value) ? 'primary' : 'default'"
						@click="setModel(item.option.value)"
					>
						{{ item.option.label }}

						<template v-if="isActive(item.option.value)" #icon>
							<Icon :size="16" name="carbon:checkmark" />
						</template>
					</n-button>
				</div>
			</n-scrollbar>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { FilterValue, FilterValuePrimitive } from "./types"
import _xor from "lodash/xor"
import { NBadge, NButton, NCard, NInput, NPopover, NScrollbar, NSpin, NTooltip } from "naive-ui"
import { computed, getCurrentInstance, inject, onBeforeUnmount, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"

const { options, multi, textInputFallback, loading, label, placeholder, embedded } = defineProps<{
	options?: { label: string; value: FilterValuePrimitive }[]
	multi?: boolean
	textInputFallback?: boolean
	loading?: boolean
	label?: string
	placeholder?: string
	embedded?: boolean
}>()

const model = defineModel<FilterValue>("value")

const textInputModel = ref<null | string>(null)
const optionsModel = ref<FilterValuePrimitive[]>([])
const optionsFilterModel = ref<null | string>(null)

// Register with FiltersContainer if available
const filtersContainer = inject<{
	registerFilter: (id: string, info: any) => void
	unregisterFilter: (id: string) => void
	updateFilter: (id: string, value: FilterValue | undefined) => void
} | null>("filtersContainer", null)

const instance = getCurrentInstance()
const filterId = instance?.uid?.toString() || `filter-${Math.random().toString(36).substr(2, 9)}`

function clearFilter() {
	model.value = multi ? [] : undefined
	optionsModel.value = []
	optionsFilterModel.value = null
	textInputModel.value = null
}

// Reconstruct optionsModel and textInputModel from the current model.value
function reconstructInternalState() {
	if (!multi || !Array.isArray(model.value) || model.value.length === 0) {
		optionsModel.value = []
		if (model.value && !Array.isArray(model.value)) {
			// Single value: check if it matches an option
			if (options && options.some(opt => `${opt.value}` === `${model.value}`)) {
				textInputModel.value = null
			} else {
				textInputModel.value = String(model.value)
			}
		} else {
			textInputModel.value = null
		}
		return
	}

	// For multi-select, separate values into options and text input
	const recognizedValues: FilterValuePrimitive[] = []
	const unrecognizedValues: string[] = []

	for (const val of model.value) {
		if (options && options.some(opt => `${opt.value}` === `${val}`)) {
			recognizedValues.push(val)
		} else {
			unrecognizedValues.push(String(val))
		}
	}

	optionsModel.value = recognizedValues
	textInputModel.value = unrecognizedValues.length > 0 ? unrecognizedValues.join(" ") : null
}

function registerFilter() {
	if (filtersContainer) {
		filtersContainer.registerFilter(filterId, {
			label: label || "Filter",
			value: model.value ?? (multi ? [] : null),
			options,
			clearFilter
		})
	}
}

const optionsFiltered = computed(() =>
	(options || []).filter(o => {
		if (!optionsFilterModel.value) {
			return true
		}
		return o.label.toLowerCase().includes(optionsFilterModel.value.toLowerCase())
	})
)

const optionsMuted = computed(() => {
	if (!options || !optionsFiltered.value) {
		return []
	}
	const filteredValues = new Set(optionsFiltered.value.map(o => `${o.value}`))
	return options.filter(o => !filteredValues.has(`${o.value}`))
})

const allOptions = computed(() => {
	const filtered = optionsFiltered.value.map(option => ({ option, isMuted: false }))
	const muted = optionsMuted.value.map(option => ({ option, isMuted: true }))
	return [...filtered, ...muted]
})

function isActive(val: FilterValuePrimitive): boolean {
	if (model.value === undefined) {
		return false
	}

	if (Array.isArray(model.value)) {
		return model.value.includes(val)
	}

	return model.value === val
}

function setModel(val?: FilterValuePrimitive) {
	if (multi) {
		if (val !== undefined) {
			optionsModel.value = _xor((optionsModel.value || []) as FilterValuePrimitive[], [val])
		}

		model.value = [...(optionsModel.value || []), ...(textInputModel.value ? [textInputModel.value] : [])]
	} else {
		if (val !== undefined) {
			if (model.value === val) {
				model.value = undefined
			} else {
				model.value = val
			}
			textInputModel.value = null
		} else {
			model.value = textInputModel.value || null
		}
	}
}

watch(
	() => model.value,
	newValue => {
		if (filtersContainer) {
			filtersContainer.updateFilter(filterId, newValue)
		}
	},
	{ immediate: true, deep: true }
)

watch(
	[() => options, () => label, () => multi, () => loading],
	() => {
		// Reconstruct state when options change, as recognized values might change
		reconstructInternalState()
		registerFilter()
	},
	{ deep: true, immediate: true }
)

onBeforeUnmount(() => {
	if (filtersContainer) {
		filtersContainer.unregisterFilter(filterId)
	}
})
</script>
