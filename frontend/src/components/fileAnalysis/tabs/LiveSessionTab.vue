<template>
	<div class="flex flex-col gap-3">
		<n-alert type="warning" :bordered="false" class="text-sm">
			This opens an interactive VNC console to the sandbox guest. CAPE boots the VM on demand and defaults its network
			route to <b>None (no internet)</b>; the desktop streams over guacd — only the control plane is proxied, the guest
			has no route out. Anything you type runs on a live malware VM.
		</n-alert>

		<div v-if="!guacUrl" class="flex min-h-52 items-center justify-center">
			<n-button type="primary" :loading="starting" @click="launch()">
				<template #icon><Icon :name="LaunchIcon" /></template>
				Launch interactive console
			</n-button>
		</div>

		<template v-else>
			<div class="flex flex-wrap items-center gap-3">
				<!-- A real anchor click always opens the tab — no popup-blocker issues -->
				<a :href="guacUrl" target="_blank" rel="noopener noreferrer">
					<n-button type="primary">
						<template #icon><Icon :name="OpenIcon" /></template>
						Open console in new tab
					</n-button>
				</a>
				<span class="text-secondary text-xs">
					Best experience — a full desktop deserves a full window. The preview below may be blank if the sandbox
					blocks embedding.
				</span>
				<div class="grow" />
				<n-button quaternary size="small" @click="guacUrl = ''">
					<template #icon><Icon :name="ResetIcon" /></template>
					Reset
				</n-button>
			</div>

			<div class="border-default overflow-hidden rounded-lg border">
				<iframe
					:src="guacUrl"
					class="h-[640px] w-full"
					title="Interactive sandbox session"
					allow="clipboard-read; clipboard-write"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NAlert, NButton, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ jobId: string }>()

const message = useMessage()
const LaunchIcon = "carbon:play"
const OpenIcon = "carbon:launch"
const ResetIcon = "carbon:reset"

const starting = ref(false)
const guacUrl = ref<string>("")

function launch() {
	starting.value = true
	Api.fileAnalysis
		.startInteractive(props.jobId)
		.then(res => {
			if (res.data.success && res.data.guac_url) {
				guacUrl.value = res.data.guac_url
			} else {
				message.warning(res.data?.message || "Could not start the interactive session.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not start the interactive session.")
		})
		.finally(() => {
			starting.value = false
		})
}
</script>
