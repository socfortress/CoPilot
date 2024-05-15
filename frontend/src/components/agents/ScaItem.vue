<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Details" tab="Details" display-directive="show">
			<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
				<KVCard v-for="(value, key) of properties" :key="key">
					<template #key>{{ key }}</template>
					<template #value>
						<template v-if="value && (key === 'end_scan' || key === 'start_scan')">
							{{ formatDate(value, dFormats.datetime) }}
						</template>
						<template v-else>{{ value ?? "-" }}</template>
					</template>
				</KVCard>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Description" tab="Description" display-directive="show">
			<div class="p-7 pt-4">
				<n-input
					:value="sca.description"
					type="textarea"
					readonly
					placeholder="Empty"
					size="large"
					:autosize="{
						minRows: 3,
						maxRows: 18
					}"
				/>
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import { NTabs, NTabPane, NInput } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { type AgentSca } from "@/types/agents.d"
import KVCard from "@/components/common/KVCard.vue"
import { computed } from "vue"
import _omit from "lodash/omit"
import "@/assets/scss/vuesjv-override.scss"

const { sca } = defineProps<{ sca: AgentSca }>()

const dFormats = useSettingsStore().dateFormat

const properties = computed(() => {
	return _omit(sca, ["description", "extract", "end_scan_text"])
})
</script>
