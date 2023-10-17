<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Checkbox</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/checkbox"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-space item-style="display: flex;" align="center">
					<n-checkbox v-model:checked="value">Checkbox</n-checkbox>
					<n-checkbox v-model:checked="value" />
					<n-checkbox v-model:checked="value" :disabled="disabled">Checkbox</n-checkbox>
					<n-button size="small" @click="disabled = !disabled">Disabled</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space item-style="display: flex;" align="center">
						<n-checkbox v-model:checked="value">Checkbox</n-checkbox>
						<n-checkbox v-model:checked="value" />
						<n-checkbox v-model:checked="value" :disabled="disabled">Checkbox</n-checkbox>
						<n-button size="small" @click="disabled = !disabled">Disabled</n-button>
					</n-space>
					`) }}

					{{
						js(`
						const value = ref(false)
						const disabled = ref(true)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Checkbox group">
				<n-checkbox-group v-model:value="cities">
					<n-space item-style="display: flex;">
						<n-checkbox value="Beijing" label="Beijing" />
						<n-checkbox value="Shanghai" label="Shanghai" />
						<n-checkbox value="Guangzhou" label="Guangzhou" />
						<n-checkbox value="Shenzen" label="Shenzhen" />
					</n-space>
				</n-checkbox-group>
				<template #code="{ html, js }">
					{{ html(`
					<n-checkbox-group v-model:value="cities">
						<n-space item-style="display: flex;">
							<n-checkbox value="Beijing" label="Beijing" />
							<n-checkbox value="Shanghai" label="Shanghai" />
							<n-checkbox value="Guangzhou" label="Guangzhou" />
							<n-checkbox value="Shenzen" label="Shenzhen" />
						</n-space>
					</n-checkbox-group>
					`) }}

					{{
						js(`
						const cities = ref(null)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Indeterminate">
				<n-space item-style="display: flex;" align="center">
					<n-checkbox v-model:checked="value" :indeterminate="indeterminate">checkbox</n-checkbox>
					<n-checkbox v-model:checked="value" :indeterminate="indeterminate" />
					<n-checkbox v-model:checked="value" :indeterminate="indeterminate" disabled />
					<n-button size="small" @click="value = !value">Check</n-button>
					<n-button size="small" @click="indeterminate = !indeterminate">Indeterminate</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space item-style="display: flex;" align="center">
						<n-checkbox v-model:checked="value" :indeterminate="indeterminate">checkbox</n-checkbox>
						<n-checkbox v-model:checked="value" :indeterminate="indeterminate" />
						<n-checkbox v-model:checked="value" :indeterminate="indeterminate" disabled />
						<n-button size="small" @click="value = !value">Check</n-button>
						<n-button size="small" @click="indeterminate = !indeterminate">Indeterminate</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NCheckbox, NSpace, NButton, NCheckboxGroup } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const value = ref(false)
const disabled = ref(true)
const cities = ref(null)
const indeterminate = ref(false)
</script>
