<template>
	<div
		class="group flex flex-col gap-0.5"
		:class="{ 'items-end text-right': message.role === 'user' }"
		data-testid="talon-v2-message"
		:data-role="message.role"
		:data-status="message.status"
	>
		<template v-if="message.role === 'user'">
			<div class="flex items-end justify-end gap-3 pl-6">
				<!-- Plain text: the prompt as talon-analyst stored and restored it. -->
				<div class="bg-secondary text-default rounded-lg px-2 py-1 text-left text-sm whitespace-pre-wrap">
					<span data-testid="talon-v2-user-text">{{ userText }}</span>
				</div>
			</div>
		</template>

		<template v-else>
			<div class="text-secondary inline-flex items-center gap-1 text-sm font-semibold">
				<span>Talon:</span>
			</div>

			<div class="flex flex-col gap-2">
				<template
					v-for="item of message.items"
					:key="item.kind === 'text' ? `t:${item.id}` : `c:${item.toolCallId}`"
				>
					<div
						v-if="item.kind === 'text'"
						class="**:text-default **:text-sm [&_*:last-child]:mb-0!"
						data-testid="talon-v2-text"
					>
						<Markdown :source="item.text" class="overflow-hidden" />
					</div>
					<TalonToolActivity v-else :item :live="message.status === 'streaming'" />
				</template>

				<div v-if="message.status === 'streaming' && !message.items.length" class="flex items-center gap-2">
					<Icon name="svg-spinners:pulse-rings-3" :size="20" />
					<span class="text-tertiary text-sm">Thinking...</span>
				</div>

				<!-- Plain text, not Markdown: talon-analyst's fixed reason, not model output. -->
				<n-alert
					v-if="message.status === 'failed'"
					type="error"
					:bordered="false"
					class="text-sm"
					data-testid="talon-v2-error"
				>
					{{ message.errorText || TALON_V2_FAILED }}
				</n-alert>
				<div
					v-else-if="message.status === 'cut_off'"
					class="text-tertiary text-xs"
					data-testid="talon-v2-cut-off"
				>
					{{ TALON_V2_CUT_OFF }}
				</div>

				<TalonUsageLine v-if="message.usage" :usage="message.usage" />
			</div>
		</template>

		<div v-if="message.createdAt" class="text-tertiary mt-1 text-xs">
			{{ formatDate(message.createdAt, dFormats.datetime) }}
		</div>
	</div>
</template>

<script setup lang="ts">
// One message of a v2 thread, from the stream or the read-back alike (`talonV2Parser`'s model).
// Only the assistant's text goes through Markdown (HTML off, as the v1 chat); every other string
// is text.
import type { TalonV2ChatMessage } from "@/types/talonV2"
import { NAlert } from "naive-ui"
import { computed } from "vue"
import { TALON_V2_CUT_OFF, TALON_V2_FAILED } from "@/api/talonV2Parser"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import TalonToolActivity from "./TalonToolActivity.vue"
import TalonUsageLine from "./TalonUsageLine.vue"

const { message } = defineProps<{ message: TalonV2ChatMessage }>()

const dFormats = useSettingsStore().dateFormat
const userText = computed(() =>
	message.items
		.filter(item => item.kind === "text")
		.map(item => item.text)
		.join("\n")
)
</script>
