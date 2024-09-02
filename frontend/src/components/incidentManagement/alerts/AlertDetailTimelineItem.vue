<template>
	<div class="alert-timeline-item" :class="{ embedded }">
		<div class="flex flex-col cursor-pointer" @click="showDetails = true">
			<div class="main-box flex flex-col gap-3 px-5 py-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">
						{{ timelineData._source.rule_description }}
					</div>
				</div>
			</div>
		</div>

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
					<div class="grid gap-2 grid-auto-fit-200 p-7 pt-4">
						<KVCard v-for="(value, key) of timelineDetailsInfo" :key="key">
							<template #key>{{ key }}</template>
							<template #value>
								<div v-if="key === '_index'">
									<code
										class="cursor-pointer text-primary-color"
										@click.stop="gotoIndex(timelineDetailsInfo._index)"
									>
										{{ timelineDetailsInfo._index }}
										<Icon :name="LinkIcon" :size="14" class="top-0.5 relative" />
									</code>
								</div>
								<div v-else>{{ value === "" ? "-" : value ?? "-" }}</div>
							</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Source" tab="Source" display-directive="show">
					<div class="p-7 pt-4" v-if="timelineDetailsSource">
						<CodeSource :code="timelineDetailsSource" lang="json" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, toRefs } from "vue"
import { NModal, NTabs, NTabPane } from "naive-ui"
import KVCard from "@/components/common/KVCard.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import _omit from "lodash/omit"
import type { AlertTimeline } from "@/types/incidentManagement/alerts.d"

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const props = defineProps<{ timelineData: AlertTimeline; embedded?: boolean }>()
const { timelineData, embedded } = toRefs(props)

const LinkIcon = "carbon:launch"
const { gotoIndex } = useGoto()
const showDetails = ref(false)
const timelineDetailsInfo = computed(() => _omit(timelineData.value, ["_source"]))
const timelineDetailsSource = computed(() => timelineData.value?._source)
</script>

<style lang="scss" scoped>
.alert-timeline-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	overflow: hidden;

	.main-box {
		.content {
			word-break: break-word;
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}
	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}
}
</style>
