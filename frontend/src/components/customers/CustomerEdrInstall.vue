<template>
	<div class="customer-edr-install flex flex-col gap-4">
		<n-spin :show="loading" class="min-h-48">
			<template v-if="commands">
				<div class="flex flex-col gap-2">
					<p class="text-secondary text-sm">
						Run the matching command on the endpoint to install and enroll the EDR agent for
						<strong>{{ customerCode }}</strong>
						.
					</p>

					<div class="flex flex-col gap-1">
						<div class="flex items-center gap-2 font-medium">
							<Icon name="mdi:microsoft-windows" :size="16" />
							Windows (PowerShell)
						</div>
						<CodeSource :code="commands.windows" lang="powershell" :max-height="220" />
					</div>

					<div class="mt-2 flex flex-col gap-1">
						<div class="flex items-center gap-2 font-medium">
							<Icon name="mdi:linux" :size="16" />
							Linux (Bash)
						</div>
						<CodeSource :code="commands.linux" lang="bash" :max-height="220" />
					</div>
				</div>
			</template>

			<template v-else>
				<n-empty v-if="!loading" class="h-48 justify-center" :description="errorMessage || 'No install commands available'">
					<div class="flex flex-col items-center gap-4">
						<n-button size="small" type="primary" @click="getCommands()">
							<template #icon>
								<Icon :name="RetryIcon" :size="14" />
							</template>
							Retry
						</n-button>
					</div>
				</n-empty>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { EDRInstallCommands } from "@/types/customers.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const RetryIcon = "carbon:restart"

const message = useMessage()
const loading = ref(false)
const commands = ref<EDRInstallCommands | null>(null)
const errorMessage = ref<string | null>(null)

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
			errorMessage.value = err.response?.data?.message || "An error occurred. Please try again later."
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getCommands()
})
</script>
