<template>
	<n-tabs type="line" animated :tabs-padding>
		<n-tab-pane v-if="alert._id" name="Agent" tab="Agent" display-directive="show">
			<div v-if="agentProperties" class="grid-auto-fit-200 grid gap-2 p-6 pt-3">
				<CardKV v-for="(value, key) of agentProperties" :key>
					<template #key>
						{{ key }}
					</template>
					<template #value>
						<template v-if="key === 'agent_id'">
							<code class="text-primary cursor-pointer" @click.stop="routeAgent(`${value}`).navigate()">
								{{ value }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
						<template v-else-if="key === 'agent_labels_customer'">
							<code
								class="text-primary cursor-pointer"
								@click.stop="
									routeCustomer(
										value ? { code: value?.toString() ?? undefined } : undefined
									).navigate()
								"
							>
								{{ value }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
						<template v-else>
							{{ value || "-" }}
						</template>
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
		<n-tab-pane
			v-if="alert._source.ask_socfortress_message"
			name="SOCFortress Response"
			tab="SOCFortress Response"
			display-directive="show"
		>
			<div class="p-6 pt-3">
				<n-input
					:value="alert._source.ask_socfortress_message"
					type="textarea"
					readonly
					placeholder="Empty"
					size="large"
					:autosize="{ minRows: 3 }"
				/>
			</div>
		</n-tab-pane>
		<n-tab-pane v-if="alert._source.message" name="Message" tab="Message" display-directive="show">
			<div class="p-6 pt-3">
				<CodeSource :code="alert._source.message" :decode="false" />
			</div>
		</n-tab-pane>
		<n-tab-pane
			v-if="alert._source.data_document"
			name="Data document"
			tab="Data document"
			display-directive="show"
		>
			<div class="p-6 pt-3">
				<n-input
					:value="alert._source.data_document"
					type="textarea"
					readonly
					placeholder="Empty"
					size="large"
					:autosize="{ minRows: 3 }"
				/>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
			<div class="p-6 pt-3">
				<CodeSource :code="alert._source" lang="json" :decode="false" />
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts"
import _pick from "lodash/pick"
import { NInput, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent } from "vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const { alert, tabsPadding = 24 } = defineProps<{
	alert: Alert
	tabsPadding?: number
}>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const LinkIcon = "carbon:launch"
const { routeCustomer, routeAgent } = useNavigation()

const agentProperties = computed(() =>
	_pick(alert._source, [
		"agent_id",
		"agent_ip_city_name",
		"agent_ip_country_code",
		"agent_ip_geolocation",
		"agent_ip_reserved_ip",
		"agent_ip",
		"agent_labels_customer",
		"agent_name"
	])
)
</script>
