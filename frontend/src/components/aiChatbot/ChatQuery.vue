<template>
	<n-collapse-transition :show="!!servers.length">
		<div class="relative flex flex-col overflow-hidden">
			<n-input
				v-model:value.trim="input"
				class="max-h-full min-h-20 pb-9"
				type="textarea"
				placeholder="How can I help you?"
				:autosize="{
					minRows: 3,
					maxRows: 18
				}"
			/>
			<div class="absolute bottom-0 left-0 right-0 flex items-center justify-between p-2 pr-3">
				<div class="flex items-center gap-1.5">
					<n-select
						v-model:value="selectedServer"
						:options="serverOptions"
						:render-option="renderOption"
						size="tiny"
						:consistent-menu-width="false"
						class="w-auto!"
					/>
					<n-popover v-if="selectedServer && selectedServerDetails" trigger="hover" class="p-0!">
						<template #trigger>
							<Icon name="carbon:help" :size="14" class="cursor-help" />
						</template>
						<div class="divide-border divide-y-1 flex flex-col">
							<div class="flex flex-col gap-1 px-3 py-2 text-sm">
								<div>{{ selectedServerDetails.name }}</div>
								<div class="text-secondary text-xs">{{ selectedServerDetails.description }}</div>
								<div v-if="selectedServerDetails.capabilities.length" class="my-1 flex flex-wrap gap-1">
									<n-tag
										v-for="item of selectedServerDetails.capabilities"
										:key="item"
										size="small"
										class="[&_.n-tag\_\_content]:leading-0 text-[10px] [&_.n-tag\_\_content]:pb-0.5"
									>
										{{ item }}
									</n-tag>
								</div>
							</div>
							<div class="px-3 py-2">
								<div class="flex items-center gap-2 text-sm">
									<div>verbose response</div>
									<n-switch v-model:value="verbose" size="small" />
								</div>
							</div>
						</div>
					</n-popover>
				</div>
				<n-button circle size="small" secondary :disabled="!isFormValid" @click="send()">
					<Icon name="carbon:arrow-up" />
					{{ loading }}
				</n-button>
			</div>
		</div>
	</n-collapse-transition>
</template>

<script setup lang="ts">
import type { RemovableRef } from "@vueuse/core"
import type { SelectOption } from "naive-ui"
import type { VNode } from "vue"
import type { MCPServer } from "@/types/copilotMCP.d"
import { useStorage } from "@vueuse/core"
import _trim from "lodash/trim"
import { NButton, NCollapseTransition, NInput, NPopover, NSelect, NSwitch, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

export interface Message {
	input: string
	verbose: boolean
	server: string
}

const props = defineProps<{ loading?: boolean }>()

const emit = defineEmits<{
	(e: "message", value: Message): void
	(e: "server-loaded"): void
}>()

const { loading } = toRefs(props)
const input = ref<string | null>(null)
const verbose = ref<boolean>(false)
const loadingServers = ref(false)
const message = useMessage()
const servers = ref<MCPServer[]>([])
const selectedServer: RemovableRef<string | null> = useStorage<string | null>(
	"ai-chatbot-selected-server",
	null,
	localStorage
)
const serverOptions = computed(() => servers.value.map(o => ({ ...o, label: o.name })))
const selectedServerDetails = computed(() => servers.value.find(o => o.value === selectedServer.value))
const isFormValid = computed(() => !!_trim(input.value || ""))

function renderOption({ node, option }: { node: VNode; option: SelectOption }) {
	return h(
		NTooltip,
		{ placement: "right", class: "max-w-40 text-xs!" },
		{
			trigger: () => node,
			default: () => option.description
		}
	)
}

function getList() {
	loadingServers.value = true

	Api.copilotMCP
		.getAvailableServers()
		.then(res => {
			if (res.data.success) {
				servers.value = res.data?.servers || []
				if (servers.value.length && !selectedServer.value) {
					selectedServer.value = servers.value[0].value
				}
				emit("server-loaded")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingServers.value = false
		})
}

function reset() {
	input.value = null
}

function send() {
	if (input.value && selectedServer.value) {
		emit("message", {
			input: input.value,
			server: selectedServer.value,
			verbose: verbose.value
		})

		reset()
	}
}

onBeforeMount(() => {
	getList()
})
</script>
