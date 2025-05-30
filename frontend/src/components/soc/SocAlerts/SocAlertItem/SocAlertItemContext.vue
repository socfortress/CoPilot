<template>
	<div class="flex flex-col gap-3">
		<n-input v-model:value="textFilter" placeholder="Search..." clearable>
			<template #prefix>
				<Icon :name="SearchIcon" />
			</template>
		</n-input>

		<div class="grid-auto-fit-200 grid gap-2">
			<CardKV v-for="{ value, key } of contextFiltered" :key="key">
				<template #key>
					{{ key }}
				</template>
				<template #value>
					<template v-if="key === 'process_name'">
						<template v-if="value && value !== '-' && value.toString() && processNameList.length">
							<div class="flex flex-wrap gap-2">
								<ThreatIntelProcessEvaluationBadge
									v-for="pn of processNameList"
									:key="pn"
									:process-name="pn"
								/>
							</div>
						</template>
						<template v-else>-</template>
					</template>
					<template v-else>
						<ExpandableText :text="value.toString() ?? '-'" :max-length="100" />
					</template>
				</template>
			</CardKV>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import _compact from "lodash/compact"
import _split from "lodash/split"
import _uniq from "lodash/uniq"
import { NInput } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"

const { alert } = defineProps<{
	alert: SocAlert
}>()
const ThreatIntelProcessEvaluationBadge = defineAsyncComponent(
	() => import("@/components/threatIntel/ThreatIntelProcessEvaluationBadge.vue")
)
const ExpandableText = defineAsyncComponent(() => import("@/components/common/ExpandableText.vue"))

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
	contextNormalized.value.filter(o => o.key.toLowerCase().includes(textFilter.value.toLowerCase()))
)
</script>
