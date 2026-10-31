<template>
	<article
		class="flex flex-col gap-2"
		:class="message.role === 'user' ? 'items-end' : 'items-start'"
		:data-role="message.role"
		:data-status="message.status"
		data-testid="talon-message"
	>
		<div class="text-secondary text-xs font-medium">
			{{ message.role === "user" ? $t("talonChat.conversation.you") : $t("talonChat.conversation.talon") }}
		</div>

		<div
			class="flex max-w-full flex-col gap-3 rounded-lg px-4 py-3 text-sm"
			:class="message.role === 'user' ? 'bg-secondary max-w-[85%]' : 'border-default w-full border'"
		>
			<template v-for="item of message.items" :key="itemKey(item)">
				<!-- Plain text with its line breaks: never HTML, never Markdown rendered as HTML. -->
				<p v-if="item.kind === 'text' && item.text" class="m-0 break-words whitespace-pre-wrap" data-testid="talon-message-text">
					<span>{{ item.text }}</span>
				</p>
				<template v-else-if="item.kind === 'soc-draft' && showCards">
					<TalonSocDraftCard :draft-id="item.draftId" :can-draft />
				</template>
				<template v-else-if="item.kind === 'analysis-offer' && showCards">
					<TalonAnalysisOfferCard :alert-id="item.alertId" :can-request="canRequestAnalysis" />
				</template>
			</template>

			<div
				v-if="message.status === 'streaming'"
				class="text-secondary flex items-center gap-2 text-xs"
				data-testid="talon-message-streaming"
			>
				<n-spin size="small" />
				{{ $t("talonChat.conversation.thinking") }}
			</div>

			<n-alert v-if="message.status === 'failed'" type="error" :bordered="false" data-testid="talon-message-error">
				{{ errorText(message.errorCode) }}
			</n-alert>
			<p v-else-if="message.status === 'cut_off'" class="text-secondary m-0 text-xs" data-testid="talon-message-cut-off">
				{{ $t("talonChat.conversation.cutOff") }}
			</p>

			<p v-if="checked" class="text-secondary m-0 text-xs" data-testid="talon-message-checked">
				<Icon name="carbon:search" :size="12" class="mr-1 inline align-[-1px]" />{{ checked }}
			</p>

			<div v-if="canRate" class="flex items-center gap-1" data-testid="talon-message-feedback">
				<n-button
					v-for="rating of RATINGS"
					:key="rating"
					size="tiny"
					quaternary
					:type="message.feedback === rating ? 'primary' : 'default'"
					:aria-pressed="message.feedback === rating"
					:aria-label="$t(`talonChat.feedback.${rating}`)"
					:title="$t(`talonChat.feedback.${rating}`)"
					:disabled="feedbackBusy"
					:data-testid="`talon-feedback-${rating}`"
					@click="emit('feedback', message.feedback === rating ? null : rating)"
				>
					<template #icon>
						<Icon :name="iconFor(rating)" />
					</template>
				</n-button>
			</div>
		</div>
	</article>
</template>

<script setup lang="ts">
import type { TalonChatItem, TalonChatMessage, TalonChatRating } from "@/types/talonChat"
import { NAlert, NButton, NSpin } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import TalonAnalysisOfferCard from "./TalonAnalysisOfferCard.vue"
import { checkedLine, errorText } from "./talonChat"
import TalonSocDraftCard from "./TalonSocDraftCard.vue"

/**
 * One turn of an "Ask Talon" conversation. Talon's text is shown as plain text with its line
 * breaks: it is the model's, so never rendered as HTML or Markdown. The "checked" line says what
 * Talon looked at, by kind; the cards are shown only to a user who may change the customer's data
 * (`showCards`), and act only through CoPilot's own routes and gates.
 */
const {
	message,
	showCards = false,
	canDraft = false,
	canRequestAnalysis = false,
	feedbackBusy = false
} = defineProps<{
	message: TalonChatMessage
	showCards?: boolean
	canDraft?: boolean
	canRequestAnalysis?: boolean
	feedbackBusy?: boolean
}>()

const emit = defineEmits<{ feedback: [rating: TalonChatRating | null] }>()

const RATINGS: TalonChatRating[] = ["up", "down"]

const checked = computed(() => (message.role === "assistant" ? checkedLine(message.checked) : null))
/** Feedback is on a completed turn, once its run id is known (read back). */
const canRate = computed(() => message.role === "assistant" && message.status === "completed" && !!message.runId)

function iconFor(rating: TalonChatRating) {
	if (rating === "up") return message.feedback === "up" ? "carbon:thumbs-up-filled" : "carbon:thumbs-up"
	return message.feedback === "down" ? "carbon:thumbs-down-filled" : "carbon:thumbs-down"
}

function itemKey(item: TalonChatItem): string {
	if (item.kind === "text") return `text-${item.id}`
	if (item.kind === "soc-draft") return `draft-${item.draftId}`
	return `offer-${item.alertId}`
}
</script>
