<template>
	<div>
		<n-spin :show="loadingList">
			<div v-if="portainerStack" class="flex flex-col gap-2">
				<CardEntity embedded>
					<template #headerMain>
						<div class="flex items-center gap-2">
							<span>#{{ portainerStack.Id }}</span>
							<span>- {{ portainerStackType }}</span>
						</div>
					</template>
					<template #headerExtra>
						<div class="flex items-center gap-2 font-sans">
							<Icon
								v-if="portainerStack.Status === PortainerStackStatus.Offline"
								:name="OfflineIcon"
								:size="16"
								class="text-warning"
							/>
							<Icon v-else :name="OnlineIcon" :size="16" class="text-success" />

							{{ portainerStack.Status === PortainerStackStatus.Online ? "Online" : "Offline" }}
						</div>
					</template>
					<template #default>
						{{ portainerStack.Name }}
					</template>
					<template #footerMain>
						<div class="flex flex-wrap items-center gap-3">
							<Badge type="splitted" color="primary">
								<template #iconLeft>
									<Icon :name="UserIcon" :size="14" />
								</template>
								<template #value>{{ portainerStack.CreatedBy }}</template>
							</Badge>
							<Badge type="splitted" color="primary">
								<template #iconLeft>
									<Icon :name="DateIcon" :size="14" />
								</template>
								<template #value>
									{{ formatDate(portainerStack.CreationDate, dFormats.datetimesec) }}
								</template>
							</Badge>
						</div>
					</template>
					<template #footerExtra>
						<div class="flex flex-wrap items-center justify-end gap-3">
							<n-button secondary size="small" @click.stop="showResourceControl = true">
								<template #icon>
									<Icon :name="ViewIcon" />
								</template>
								ResourceControl
							</n-button>
							<n-button
								v-if="portainerStack.Status === PortainerStackStatus.Online"
								:loading="loadingAction"
								type="warning"
								secondary
								size="small"
								@click.stop="stop()"
							>
								<template #icon>
									<Icon :name="StopIcon" />
								</template>
								Stop Worker
							</n-button>
							<n-button
								v-if="portainerStack.Status === PortainerStackStatus.Offline"
								:loading="loadingAction"
								type="success"
								secondary
								size="small"
								@click.stop="start()"
							>
								<template #icon>
									<Icon :name="StartIcon" />
								</template>
								Start Worker
							</n-button>
						</div>
					</template>
				</CardEntity>

				<div class="grid-auto-fit-250 grid gap-2">
					<CardKV v-for="(value, key) of properties" :key>
						<template #key>
							{{ key }}
						</template>
						<template #value>
							{{ value ?? "-" }}
						</template>
					</CardKV>
				</div>
			</div>

			<div v-else class="min-h-96">
				<n-empty v-if="!loadingList" description="No Portainer Stack found" class="h-48 justify-center" />
			</div>

			<n-modal
				v-model:show="showResourceControl"
				preset="card"
				content-class="@container"
				:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
				:bordered="false"
				title="Resource Control"
			>
				<div class="flex flex-col gap-4 @2xl:flex-row!">
					<SimpleJsonViewer
						v-if="portainerStack"
						class="vuesjv-override grow"
						:model-value="portainerStack?.ResourceControl"
						:initial-expanded-depth="2"
					/>

					<div class="min-w-40">
						<CardKV>
							<template #key>Type legend</template>
							<template #value>
								<ul class="list-none p-0">
									<li>1 = Container</li>
									<li>2 = Service</li>
									<li>3 = Volume</li>
									<li>4 = Network</li>
									<li>5 = Secret</li>
									<li>6 = Stack</li>
									<li>7 = Config</li>
								</ul>
							</template>
						</CardKV>
					</div>
				</div>
			</n-modal>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SafeAny } from "@/types/common.d"
import type { PortainerStack } from "@/types/portainer.d"
import _castArray from "lodash/castArray"
import _pick from "lodash/pick"
import { NButton, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { PortainerStackStatus } from "@/types/portainer.d"
import { formatDate } from "@/utils"
import "@/assets/scss/overrides/vuesjv-override.scss"

const { stackId } = defineProps<{ stackId: number }>()

const OfflineIcon = "carbon:error-filled"
const OnlineIcon = "carbon:checkmark-filled"
const UserIcon = "carbon:group-security"
const DateIcon = "carbon:time"
const ViewIcon = "iconoir:eye-solid"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const message = useMessage()
const showResourceControl = ref(false)
const loadingList = ref(false)
const loadingAction = ref(false)
const dFormats = useSettingsStore().dateFormat
const portainerStack = ref<PortainerStack | null>(null)
const portainerStackType = computed(
	() => ["", "Docker Swarm stack", "Standalone Docker stack", "Kubernetes stack"][portainerStack.value?.Type || 0]
)

const properties = computed(() => {
	const props: Partial<{ [key in keyof PortainerStack]: SafeAny | null | Date }> = _pick(portainerStack.value || {}, [
		"EndpointId",
		"SwarmId",
		"EntryPoint",
		"Env",
		"ProjectPath",
		"UpdateDate",
		"UpdatedBy",
		"AdditionalFiles",
		"AutoUpdate",
		"Option",
		"GitConfig",
		"FromAppTemplate",
		"Namespace",
		"IsComposeFormat"
	])

	props.Env = _castArray(props.Env).join(", ") || null
	props.UpdateDate = props.UpdateDate
		? formatDate(props.UpdateDate as string | number | Date, dFormats.datetimesec)
		: null
	props.UpdatedBy = props.UpdatedBy || null
	props.Namespace = props.Namespace || null

	return props
})

function getPortainerStack() {
	loadingList.value = true

	Api.portainer
		.getStackDetails(stackId)
		.then(res => {
			if (res.data.success) {
				portainerStack.value = res.data.data
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingList.value = false
		})
}

function stop() {
	loadingAction.value = true

	Api.portainer
		.stopWazuhCustomerStack(stackId)
		.then(res => {
			if (res.data.success) {
				portainerStack.value = res.data.data
				message.success(`Wazuh Worker stopped${res.data?.message ? `: ${res.data.message}` : ""}`)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAction.value = false
		})
}

function start() {
	loadingAction.value = true

	Api.portainer
		.startWazuhCustomerStack(stackId)
		.then(res => {
			if (res.data.success) {
				portainerStack.value = res.data.data
				message.success(`Wazuh Worker started${res.data?.message ? `: ${res.data.message}` : ""}`)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAction.value = false
		})
}

onBeforeMount(() => {
	getPortainerStack()
})
</script>
