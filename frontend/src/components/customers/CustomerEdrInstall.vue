<template>
	<div class="flex max-w-full flex-col gap-4 overflow-hidden">
		<n-spin :show="loading" class="min-h-48">
			<template v-if="commands">
				<div class="flex flex-col gap-4">
					<n-alert type="info" :bordered="false">
						Run the matching command on the endpoint to install and enroll the EDR agent for
						<Badge type="splitted" color="primary" size="small" class="mx-1 inline-flex align-middle">
							<template #label>Customer</template>
							<template #value>{{ customerCode }}</template>
						</Badge>
					</n-alert>

					<CardEntity v-for="section in installCommandSections" :key="section.platform" embedded size="small">
						<template #headerMain>
							<PlatformBadge :platform="section.platform" />
						</template>
						<template #headerExtra>
							<Badge type="splitted" size="small">
								<template #label>Shell</template>
								<template #value>{{ section.shell }}</template>
							</Badge>
						</template>
						<template #default>
							<CodeSource :code="section.code" :lang="section.lang" :max-height="220" />
						</template>
					</CardEntity>
				</div>
			</template>

			<template v-else>
				<n-empty
					v-if="!loading"
					class="h-48 justify-center"
					:description="errorMessage || 'No install commands available'"
				/>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { EDRInstallCommands } from "@/types/customers.d"
import { NAlert, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import { getApiErrorMessage } from "@/utils"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const message = useMessage()
const loading = ref(false)
const commands = ref<EDRInstallCommands | null>(null)
const errorMessage = ref<string | null>(null)

const installCommandSections = computed(() => {
	const cmds = commands.value
	if (!cmds) return []

	return [
		{ platform: "windows", shell: "PowerShell", lang: "powershell", code: cmds.windows },
		{ platform: "linux", shell: "Bash", lang: "bash", code: cmds.linux }
	]
})

function getCommands() {
	loading.value = true
	errorMessage.value = null

	Api.customers
		.getEdrInstallCommands(customerCode)
		.then(res => {
			if (res.data.success) {
				commands.value = res.data.commands
			} else {
				commands.value = null
				errorMessage.value = res.data?.message || "An error occurred. Please try again later."
				message.warning(errorMessage.value)
			}
		})
		.catch(err => {
			commands.value = null
			errorMessage.value = getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later."
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getCommands()
})
</script>
