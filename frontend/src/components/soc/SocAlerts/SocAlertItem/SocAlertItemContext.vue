<template>
	<div class="flex flex-col gap-3">
		<n-input placeholder="Search..." v-model:value="textFilter" clearable>
			<template #prefix>
				<Icon :name="SearchIcon" />
			</template>
		</n-input>

		<div class="grid gap-2 grid-auto-flow-200">
			<KVCard v-for="{ value, key } of contextFiltered" :key="key">
				<template #key>{{ key }}</template>
				<template #value>
					<template v-if="key === 'process_name'">
						<template v-if="value && value !== '-' && value.toString() && processNameList.length">
							<div class="flex flex-wrap gap-2">
								<SocAlertItemEvaluation v-for="pn of processNameList" :key="pn" :process-name="pn" />
							</div>
						</template>
						<template v-else>-</template>
					</template>
					<template v-else>
						<ExpandableText :text="value.toString() ?? '-'" :maxLength="100" />
					</template>
				</template>
			</KVCard>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import KVCard from "@/components/common/KVCard.vue"
import { NInput } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { computed, defineAsyncComponent, ref } from "vue"
import _split from "lodash/split"
import _compact from "lodash/compact"
import _uniq from "lodash/uniq"
const SocAlertItemEvaluation = defineAsyncComponent(() => import("./SocAlertItemEvaluation.vue"))
const ExpandableText = defineAsyncComponent(() => import("@/components/common/ExpandableText.vue"))

const { alert } = defineProps<{
	alert: SocAlert
}>()

const SearchIcon = "carbon:search"

const textFilter = ref("")
const processNameList = computed(() =>
	_uniq(
		_compact(
			_split(alert.alert_context?.process_name || "", ",").filter(
				p => p.toLowerCase() !== "no process name found"
			)
		)
	)
)
const contextNormalized = computed(() => {
	const list = []
	for (const key in alert.alert_context) {
		list.push({
			key,
			value: alert.alert_context[key]
		})
	}

	return list
})

const contextFiltered = computed(() =>
	contextNormalized.value.filter(o => o.key.toLowerCase().indexOf(textFilter.value.toLowerCase()) !== -1)
)
</script>
