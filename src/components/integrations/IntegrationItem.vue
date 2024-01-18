<template>
	<div class="integration-item">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ integration.id }}</div>
				<div class="actions">
					<Badge type="cursor" @click="showDetails = true">
						<template #iconLeft>
							<Icon :name="DetailsIcon" :size="14"></Icon>
						</template>
						<template #value>Details</template>
					</Badge>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ integration.integration_name }}</div>
					<div class="description">
						{{ integration.description }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge v-for="authKey of integration.auth_keys" :key="authKey.auth_key_name">
					<template #value>{{ authKey.auth_key_name }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="integration.integration_name"
			:bordered="false"
			segmented
		>
			<!--
				<div v-html="compiledMarkdown"></div>
			-->
			<vue-markdown-it :source="integration.integration_details" class="integration-details" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref, toRefs } from "vue"
import { NModal } from "naive-ui"
import type { AvailableIntegration } from "@/types/integrations"

// TODO: choose one way end remove others from package.json
// import { marked } from "marked"
// @ts-ignore
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"

const props = defineProps<{
	integration: AvailableIntegration
}>()
const { integration } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"

const showDetails = ref(false)

// const compiledMarkdown = computed(() => marked(integration.value.integration_details))
</script>

<style lang="scss" scoped>
.integration-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-size: 13px;
		.id {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}

.integration-details {
	:deep() {
		& > * {
			margin-bottom: 15px;
		}
	}
}
</style>
