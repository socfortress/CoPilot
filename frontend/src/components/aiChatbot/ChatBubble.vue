<template>
	<div
		class="flex flex-col gap-0.5"
		:class="{
			'items-end text-right': entity.sender === 'user'
		}"
	>
		<div
			class="text-secondary inline-flex items-center gap-1 text-sm font-semibold"
			v-if="entity.sender === 'server'"
		>
			<span>{{ entity.server }}:</span>

			<span
				class="text-tertiary inline-flex cursor-pointer items-center gap-1"
				v-if="thought && isThoughtVisible"
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

			<div v-if="isCopySupported" class="flex justify-end">
				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" text @click="copyLink()">
							<template #icon>
								<Icon name="carbon:copy" :size="12" />
							</template>
						</n-button>
					</template>
					<div class="text-xs">{{ showCopyTooltip ? "Copied!" : "Copy" }}</div>
				</n-tooltip>
			</div>
		</div>
		<div
			class="[&_>*:last-child]:mb-2! [&_*]:text-sm"
			:class="{
				'bg-secondary max-w-11/12 rounded-lg px-2 py-1 text-sm': entity.sender === 'user'
			}"
		>
			<template v-if="entity.sender === 'user'">
				{{ entity.body }}
			</template>
			<template v-else>
				<div v-if="thought && isThoughtVisible">
					<CollapseKeepAlive :show="!isThoughtCollapsed">
						<div class="text-secondary bg-secondary mb-2 rounded-md px-1 py-2 [&_*]:text-[10px]">
							<Suspense>
								<Markdown :source="thought" class="animate-fade" @mounted="isThoughtMounted = true" />
							</Suspense>
							<div v-if="!isThoughtMounted">
								{{ thought }}
							</div>
						</div>
					</CollapseKeepAlive>
				</div>
				<Suspense v-if="body && isBodyVisible">
					<Markdown :source="body" class="animate-fade" @mounted="isBodyMounted = true" />
				</Suspense>
				<div v-if="!isBodyMounted">
					{{ body }}
				</div>
			</template>
		</div>
		<div class="text-tertiary text-xs">
			{{ formatDate(entity.datetime, dFormats.datetime) }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Markdown from "@/components/common/Markdown.vue"
import Icon from "@/components/common/Icon.vue"
import { onMounted, ref, type Ref } from "vue"
import { NTooltip, NButton } from "naive-ui"
import { useClipboard } from "@vueuse/core"

export interface ChatBubble {
	id: string
	datetime: Date
	body: string
	thought?: string
	server: string
	new?: boolean
	sender: "user" | "server"
}

const emit = defineEmits<{
	(e: "update"): void
}>()

const { entity } = defineProps<{ entity: ChatBubble }>()

const dFormats = useSettingsStore().dateFormat
const { copy: copyLink, copied: showCopyTooltip, isSupported: isCopySupported } = useClipboard({ source: entity.body })

const isThinking = ref(false)
const isThoughtCollapsed = ref(false)
const isThoughtVisible = ref(false)
const isThoughtMounted = ref(false)
const isBodyVisible = ref(false)
const isBodyMounted = ref(false)

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

onMounted(() => {
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
})
</script>
