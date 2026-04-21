<template>
	<div class="group flex flex-col gap-0.5" :class="{ 'items-end text-right': msg.sender === 'user' }">
		<template v-if="msg.sender === 'server'">
			<div class="text-secondary inline-flex items-center gap-1 text-sm font-semibold">
				<span>Talon:</span>
				<div
					v-if="isCopySupported"
					class="pointer-events-none ml-1 flex items-center opacity-0 transition-opacity duration-300 group-hover:pointer-events-auto group-hover:opacity-100"
				>
					<n-tooltip>
						<template #trigger>
							<n-button size="tiny" text @click="copyText(msg.body)">
								<template #icon>
									<Icon name="carbon:copy" :size="13" />
								</template>
							</n-button>
						</template>
						<div class="text-xs">Copy</div>
					</n-tooltip>
				</div>
			</div>
			<div class="**:text-default **:text-sm [&_*:last-child]:mb-0!">
				<Markdown :source="msg.body" class="overflow-hidden" />
			</div>
		</template>

		<template v-if="msg.sender === 'user'">
			<div class="flex items-end justify-end gap-3 pl-6">
				<div class="bg-secondary **:text-default rounded-lg px-2 py-1 text-sm [&_*:last-child]:mb-0!">
					<Markdown :source="msg.body" class="overflow-hidden" />
				</div>
			</div>
		</template>

		<div class="text-tertiary mt-1 text-xs">
			{{ formatDate(msg.datetime, dFormats.datetime) }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { useClipboard } from "@vueuse/core"
import { NButton, NTooltip } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

export interface TalonMessage {
	id: string
	datetime: Date
	body: string
	sender: "user" | "server"
}

defineProps<{
	msg: TalonMessage
}>()

const dFormats = useSettingsStore().dateFormat
const { copy: copyText, isSupported: isCopySupported } = useClipboard()
</script>
