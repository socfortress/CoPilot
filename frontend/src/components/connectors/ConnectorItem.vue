<template>
	<n-spin :show="loading" class="connector-item">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="main-box flex gap-6">
				<div class="content flex flex-col gap-2 grow">
					<div class="flex gap-4">
						<div class="avatar">
							<n-avatar
								class="connector-image"
								object-fit="contain"
								round
								:size="40"
								:src="`/images/connectors/${
									connector ? connector.connector_name.toLowerCase() + '.svg' : 'default-logo.svg'
								}`"
								:alt="`${connector.connector_name} Logo`"
								fallback-src="/images/img-not-found.svg"
							/>
						</div>

						<div class="info flex flex-col gap-2">
							<div class="name">{{ connector.connector_name }}</div>
							<div class="description" v-if="connector.connector_description">
								{{ connector.connector_description }}
							</div>
							<div class="extra-data" v-if="connector.connector_extra_data">
								{{ connector.connector_extra_data }}
							</div>
						</div>
					</div>

					<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
						<Badge :type="connector.connector_configured ? 'active' : 'muted'">
							<template #iconRight>
								<Icon
									:name="connector.connector_configured ? EnabledIcon : DisabledIcon"
									:size="14"
								></Icon>
							</template>
							<template #label>Configured</template>
						</Badge>

						<Badge :type="connector.connector_verified ? 'active' : 'muted'">
							<template #iconRight>
								<Icon
									:name="connector.connector_verified ? EnabledIcon : DisabledIcon"
									:size="14"
								></Icon>
							</template>
							<template #label>Verified</template>
						</Badge>
					</div>
				</div>

				<div class="actions-box flex flex-col gap-2 justify-center">
					<n-button
						type="primary"
						v-if="!connector.connector_verified"
						@click="verify(connector)"
						:loading="loadingVerify"
						size="small"
					>
						<template #icon>
							<Icon :name="VerifyIcon"></Icon>
						</template>
						Verify
					</n-button>

					<n-button
						:type="!connector.connector_configured ? 'primary' : undefined"
						:loading="loadingConfiguration"
						@click="openConfigDialog()"
						size="small"
					>
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>

						{{ !connector.connector_configured ? "Configure" : "Update" }}
					</n-button>
				</div>
			</div>
		</div>

		<n-modal
			title="Connector configuration"
			v-model:show="showConfigDialog"
			:mask-closable="false"
			:close-on-esc="false"
			width="600px"
		>
			<n-card style="width: 90vw; max-width: 500px">
				<ConfigForm
					v-if="showConfigDialog"
					@loading="loadingConfiguration = $event"
					:connector="connector"
					@close="closeConfigDialog"
				/>
			</n-card>
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref, toRefs } from "vue"
import Api from "@/api"
import { NAvatar, useMessage, NModal, NSpin, NButton, NCard } from "naive-ui"
import type { Connector } from "@/types/connectors.d"
import ConfigForm from "./ConfigForm"

const emit = defineEmits<{
	(e: "verified"): void
	(e: "updated"): void
}>()

const props = defineProps<{
	connector: Connector
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

<style lang="scss" scoped>
.connector-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.main-box {
		.connector-image {
			border: 2px solid var(--bg-body);
			min-width: 40px;
			min-height: 40px;
		}
		.content {
			word-break: break-word;

			.name {
				font-weight: bold;
			}
			.description {
				font-size: 13px;
			}
			.extra-data {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
