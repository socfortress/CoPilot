<template>
	<div>
		<CardEntity :loading>
			<template #default>
				<div class="flex items-start gap-4">
					<n-avatar
						class="mt-0.5"
						object-fit="contain"
						round
						:size="40"
						:src="`/images/connectors/${
							connector ? `${connector.connector_name.toLowerCase()}.svg` : 'default-logo.svg'
						}`"
						:alt="`${connector.connector_name} Logo`"
						fallback-src="/images/img-not-found.svg"
					/>

					<div class="flex flex-col gap-1">
						<div>
							{{ connector.connector_name }}
						</div>
						<div v-if="connector.connector_description">
							{{ connector.connector_description }}
						</div>
						<p v-if="connector.connector_extra_data">
							{{ connector.connector_extra_data }}
						</p>
					</div>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge :type="connector.connector_configured ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="connector.connector_configured ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Configured</template>
					</Badge>

					<Badge :type="connector.connector_verified ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="connector.connector_verified ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Verified</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<div class="flex flex-wrap justify-end gap-2">
					<n-button
						v-if="!connector.connector_verified"
						type="primary"
						:loading="loadingVerify"
						size="small"
						@click="verify(connector)"
					>
						<template #icon>
							<Icon :name="VerifyIcon" />
						</template>
						Verify
					</n-button>

					<n-button
						:type="!connector.connector_configured ? 'primary' : undefined"
						:loading="loadingConfiguration"
						size="small"
						@click="openConfigDialog()"
					>
						<template #icon>
							<Icon :name="DetailsIcon" />
						</template>

						{{ !connector.connector_configured ? "Configure" : "Update" }}
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showConfigDialog"
			title="Connector configuration"
			:mask-closable="false"
			:close-on-esc="false"
			width="600px"
		>
			<n-card style="width: 90vw; max-width: 500px">
				<ConfigForm
					v-if="showConfigDialog"
					:connector="connector"
					@loading="loadingConfiguration = $event"
					@close="closeConfigDialog"
				/>
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Connector } from "@/types/connectors.d"
import { NAvatar, NButton, NCard, NModal, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ConfigForm from "./ConfigForm"

const props = defineProps<{
	connector: Connector
}>()

const emit = defineEmits<{
	(e: "verified"): void
	(e: "updated"): void
}>()

const { connector } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"
const VerifyIcon = "carbon:settings-check"
const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ri:check-line"

const showConfigDialog = ref(false)
const loadingConfiguration = ref(false)
const loadingVerify = ref(false)
const message = useMessage()

const loading = computed(() => loadingVerify.value || loadingConfiguration.value)

function openConfigDialog() {
	showConfigDialog.value = true
}
function closeConfigDialog(update: boolean) {
	showConfigDialog.value = false
	loadingConfiguration.value = false

	if (update) {
		emit("updated")
	}
}

function verify(connector: Connector) {
	loadingVerify.value = true

	Api.connectors
		.verify(connector.id)
		.then(res => {
			message.success(res.data?.message || "Connector was successfully verified.")
			emit("verified")
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingVerify.value = false
		})
}
</script>
