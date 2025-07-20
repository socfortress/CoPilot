<template>
	<div>
		<div class="ai-chatbot-button-wrapper w-15 fixed bottom-10 right-0 h-10" @click="showDrawer = true">
			<n-tooltip trigger="hover" placement="left">
				<template #trigger>
					<n-float-button type="primary" class="ai-chatbot-button">
						<Icon name="carbon:chat-bot" />
					</n-float-button>
				</template>

				AI Chatbot
			</n-tooltip>
		</div>

		<n-drawer
			v-model:show="showDrawer"
			:width="400"
			class="max-w-[90vw]"
			display-directive="show"
			:trap-focus="false"
		>
			<n-drawer-content title="AI Chatbot" closable body-content-class="p-0! overflow-hidden! flex flex-col">
				<ChatContainer class="grow" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { NDrawer, NDrawerContent, NFloatButton, NTooltip } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import ChatContainer from "./ChatContainer.vue"

const showDrawer = ref(false)
</script>

<style lang="scss" scoped>
.ai-chatbot-button-wrapper {
	.ai-chatbot-button {
		transition: all 0.25s var(--bezier-ease);
		right: 20px;

		:deep() {
			.n-float-button__body {
				display: flex;
				align-items: start;
				padding-left: 11px;
			}
		}
	}
	&:not(:hover) {
		.ai-chatbot-button {
			width: 54px !important;
			right: -20px;
		}
	}
}
</style>
