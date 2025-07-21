<template>
	<div
		class="group flex flex-col gap-0.5"
		:class="{
			'items-end text-right': entity.sender === 'user'
		}"
	>
		<template v-if="entity.sender === 'server'">
			<div class="text-secondary inline-flex items-center gap-1 text-sm font-semibold">
				<span>{{ entity.server }}:</span>

				<span
					v-if="thought && isThoughtVisible"
					class="text-tertiary inline-flex cursor-pointer items-center gap-1"
					@click="isThoughtCollapsed = !isThoughtCollapsed"
				>
					{{ isThinking ? "thinking..." : "thought" }}

					<Icon
						name="carbon:chevron-right"
						:size="14"
						class="transition-transform"
						:class="{ 'rotate-90': !isThoughtCollapsed }"
					/>
				</span>

				<div
					v-if="isCopySupported"
					class="pointer-events-none ml-1 flex items-center opacity-0 transition-opacity duration-300 group-hover:pointer-events-auto group-hover:opacity-100"
				>
					<n-tooltip>
						<template #trigger>
							<n-button size="tiny" text @click="copyLink()">
								<template #icon>
									<Icon name="carbon:copy" :size="13" />
								</template>
							</n-button>
						</template>
						<div class="text-xs">{{ showCopyTooltip ? "Copied!" : "Copy" }}</div>
					</n-tooltip>
				</div>
			</div>

			<div v-if="thought && isThoughtVisible">
				<CollapseKeepAlive :show="!isThoughtCollapsed">
					<div class="text-secondary bg-secondary mb-2 rounded-md px-1 py-2 [&_*]:text-[10px]">
						<Markdown :source="thought" class="animate-fade" />
					</div>
				</CollapseKeepAlive>
			</div>
			<div v-if="body && isBodyVisible" class="[&_*:last-child]:mb-0! [&_*]:text-sm">
				<Markdown :source="body" class="animate-fade" />
			</div>
		</template>

		<template v-if="entity.sender === 'user'">
			<div class="flex items-end justify-end gap-3 pl-6">
				<div
					class="pointer-events-none mb-1 flex items-center gap-3 opacity-0 transition-opacity duration-300 group-hover:pointer-events-auto group-hover:opacity-100"
				>
					<div v-if="isCopySupported" class="flex items-center">
						<n-tooltip>
							<template #trigger>
								<n-button size="tiny" text @click="copyLink()">
									<template #icon>
										<Icon name="carbon:copy" :size="13" />
									</template>
								</n-button>
							</template>
							<div class="text-xs">{{ showCopyTooltip ? "Copied!" : "Copy" }}</div>
						</n-tooltip>
					</div>
					<div class="flex items-center">
						<n-tooltip>
							<template #trigger>
								<n-button size="tiny" text @click="copyLink()">
									<template #icon>
										<Icon name="carbon:edit" :size="13" />
									</template>
								</n-button>
							</template>
							<div class="text-xs">Edit</div>
						</n-tooltip>
					</div>
				</div>
				<div class="bg-secondary [&_*:last-child]:mb-0! [&_*]:text-white! rounded-lg px-2 py-1 text-sm">
					<Markdown :source="entity.body" class="animate-fade" />
				</div>
			</div>
		</template>

		<div class="text-tertiary mt-1 text-xs">
			{{ formatDate(entity.datetime, dFormats.datetime) }}
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Ref } from "vue"
import { useClipboard } from "@vueuse/core"
import { NButton, NTooltip } from "naive-ui"
import { onMounted, ref } from "vue"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

export interface ChatBubble {
	id: string
	datetime: Date
	body: string
	thought?: string
	server: string
	new?: boolean
	sender: "user" | "server"
}

const { entity } = defineProps<{ entity: ChatBubble }>()

const emit = defineEmits<{
	(e: "update"): void
}>()

const dFormats = useSettingsStore().dateFormat
const { copy: copyLink, copied: showCopyTooltip, isSupported: isCopySupported } = useClipboard({ source: entity.body })

const isThinking = ref(false)
const isThoughtCollapsed = ref(false)
const isThoughtVisible = ref(false)
const isBodyVisible = ref(false)

const thought = ref("")
const body = ref("")

function startTypingEffect(text: string, variable: Ref<string>, duration = 2000) {
	variable.value = ""

	const totalChars = text.length
	if (totalChars === 0) return

	const delay = duration / totalChars
	let currentIndex = 0

	const interval = setInterval(() => {
		variable.value += text[currentIndex]
		currentIndex++

		if (currentIndex >= totalChars) {
			clearInterval(interval)
			emit("update")
		}
	}, delay)
}

function setAnimation() {
	if (entity.new) {
		if (entity.thought) {
			isThinking.value = true
			isThoughtVisible.value = true
			startTypingEffect(entity.thought, thought, 2000)
			setTimeout(() => {
				isThinking.value = false
				isBodyVisible.value = true
				startTypingEffect(entity.body, body, 4000)
			}, 2000)
		} else {
			isBodyVisible.value = true
			startTypingEffect(entity.body, body, 4000)
		}
	} else {
		if (entity.thought) {
			isThoughtCollapsed.value = true
			isThoughtVisible.value = true
			thought.value = entity.thought
		}

		isBodyVisible.value = true
		body.value = entity.body
	}
}

onMounted(() => {
	setAnimation()
})
</script>
