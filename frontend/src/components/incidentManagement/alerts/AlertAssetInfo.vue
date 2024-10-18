<template>
	<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
		<CardKV v-for="(value, key) of asset" :key="key">
			<template #key>
				{{ key }}
			</template>
			<template #value>
				<div v-if="key === 'id'">#{{ value }}</div>
				<div v-else-if="key === 'customer_code'">
					<code class="text-primary cursor-pointer" @click.stop="gotoCustomer({ code: asset.customer_code })">
						#{{ asset.customer_code }}
						<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
					</code>
				</div>
				<div v-else-if="key === 'agent_id'">
					<code class="text-primary cursor-pointer" @click.stop="gotoAgent(asset.agent_id)">
						{{ asset.agent_id }}
						<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
					</code>
				</div>
				<div v-else-if="key === 'index_name'">
					<code class="text-primary cursor-pointer" @click.stop="gotoIndex(asset.index_name)">
						{{ asset.index_name }}
						<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
					</code>
				</div>
				<div v-else-if="key === 'index_id'">
					<code class="text-primary cursor-pointer" @click.stop="openAlertDetails()">
						{{ asset.index_id }}
						<Icon :name="ViewIcon" :size="14" class="relative top-0.5" />
					</code>
				</div>
				<div v-else>
					{{ value === "" ? "-" : (value ?? "-") }}
				</div>
			</template>
		</CardKV>
	</div>

	<n-modal
		v-model:show="showAlertDetails"
		preset="card"
		content-class="!p-0"
		:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
		:bordered="false"
		title="Alert Details"
		segmented
	>
		<n-spin :show="loading" class="min-h-40">
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of alertDetailsInfo" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								<div v-if="key === '_index'">
									<code
										class="text-primary cursor-pointer"
										@click.stop="gotoIndex(alertDetailsInfo._index)"
									>
										{{ alertDetailsInfo._index }}
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
					<div v-if="alertDetailsSource" class="p-7 pt-4">
						<CodeSource :code="alertDetailsSource" lang="json" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-spin>
	</n-modal>
</template>

<script setup lang="ts">
import type { AlertAsset, AlertDetails } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import _omit from "lodash/omit"
import { NModal, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs, watch } from "vue"

const props = defineProps<{ asset: AlertAsset }>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { asset } = toRefs(props)

const LinkIcon = "carbon:launch"
const ViewIcon = "iconoir:eye-alt"
const { gotoAgent, gotoIndex, gotoCustomer } = useGoto()
const message = useMessage()
const loading = ref(false)
const showAlertDetails = ref(false)
const alertDetails = ref<AlertDetails | null>(null)
const alertDetailsInfo = computed(() => _omit(alertDetails.value, ["_source"]))
const alertDetailsSource = computed(() => alertDetails.value?._source)

watch(showAlertDetails, val => {
	if (val && !alertDetails.value) {
		getAlertDetails(asset.value.index_id, asset.value.index_name)
	}
})

function getAlertDetails(indexId: string, indexName: string) {
	loading.value = true

	Api.incidentManagement
		.getAlertDetails(indexId, indexName)
		.then(res => {
			if (res.data.success) {
				alertDetails.value = res.data?.alert_details || null
			} else {
				closeAlertDetails()
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			closeAlertDetails()
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function openAlertDetails() {
	showAlertDetails.value = true
}

function closeAlertDetails() {
	showAlertDetails.value = false
}
</script>
