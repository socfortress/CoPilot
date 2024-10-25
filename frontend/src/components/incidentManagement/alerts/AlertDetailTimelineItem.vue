<template>
	<div>
		<CardEntity :embedded hoverable clickable @click="showDetails = true">
			{{ timelineData._source.rule_description }}
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(700px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:bordered="false"
			title="Timeline Details"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of timelineDetailsInfo" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<div v-if="key === '_index'">
									<code
										class="text-primary cursor-pointer"
										@click.stop="gotoIndex(timelineDetailsInfo._index)"
									>
										{{ timelineDetailsInfo._index }}
										<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
									</code>
								</div>
								<div v-else>
									{{ value === "" ? "-" : (value ?? "-") }}
								</div>
							</template>
						</CardKV>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Source" tab="Source" display-directive="show">
					<div v-if="timelineDetailsSource" class="p-7 pt-4">
						<CodeSource :code="timelineDetailsSource" lang="json" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertTimeline } from "@/types/incidentManagement/alerts.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import _omit from "lodash/omit"
import { NModal, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs } from "vue"

const props = defineProps<{ timelineData: AlertTimeline; embedded?: boolean }>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { timelineData, embedded } = toRefs(props)

const LinkIcon = "carbon:launch"
const { gotoIndex } = useGoto()
const showDetails = ref(false)
const timelineDetailsInfo = computed(() => _omit(timelineData.value, ["_source"]))
const timelineDetailsSource = computed(() => timelineData.value?._source)
</script>
