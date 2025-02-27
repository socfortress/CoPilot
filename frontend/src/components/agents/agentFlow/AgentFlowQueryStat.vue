<template>
	<div>
		<CardEntity :embedded hoverable clickable @click.stop="showDetails = true">
			<template #headerMain>
				<div class="flex grow flex-wrap gap-2">
					<span>
						{{ formatDate(stat.first_active, dFormats.datetimesecmill) }}
					</span>
					<span>•</span>
					<span>
						{{ formatDate(stat.last_active, dFormats.datetimesecmill) }}
					</span>
				</div>
			</template>
			<template #default>
				<div class="flex flex-wrap gap-2">
					<Badge v-for="artifact of stat.names_with_response" :key="artifact" color="primary" type="splitted">
						<template #value>
							{{ artifact }}
						</template>
					</Badge>
				</div>
				<div v-if="stat.error_message" class="text-error mt-3">
					{{ stat.error_message }}
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #label>Status</template>
						<template #value>
							{{ stat.status || "-" }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #label>Duration</template>
						<template #value>
							{{ duration }}
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`Agent Query Stat ${stat.Artifact ? `: ${stat.Artifact}` : ''}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of properties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								{{ value === "" ? "-" : (value ?? "-") }}
							</template>
						</CardKV>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Backtrace" tab="Backtrace" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="stat.backtrace"
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
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FlowQueryStat } from "@/types/flow.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import dayjs from "@/utils/dayjs"
import _pick from "lodash/pick"
import { NInput, NModal, NTabPane, NTabs } from "naive-ui"
import { computed, ref } from "vue"

const { stat, embedded } = defineProps<{ stat: FlowQueryStat; embedded?: boolean }>()

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const duration = computed(() => dayjs.duration(stat.duration).humanize())

const properties = computed(() => {
	return _pick(stat, [
		"Artifact",
		"log_rows",
		"uploaded_files",
		"uploaded_bytes",
		"expected_uploaded_bytes",
		"result_rows",
		"query_id",
		"total_queries"
	])
})
</script>
