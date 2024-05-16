<template>
	<div class="sca-result-item" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex items-center">
				<div class="id">#{{ data.id }}</div>
				<div class="grow"></div>
				<div class="actions">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ data.title }}</div>
					<div class="description">$ {{ data.command }}</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge
					type="splitted"
					:color="
						data.result === 'failed' ? 'danger' : data.result === 'not applicable' ? 'warning' : 'success'
					"
					class="uppercase"
				>
					<template #label>{{ data.result }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Compliance</template>
					<template #value>{{ data.compliance?.length || "-" }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Condition</template>
					<template #value>{{ data.condition || "-" }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>Rules</template>
					<template #value>{{ data.rules?.length || "-" }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="data?.title"
			:bordered="false"
			segmented
		>
			<ScaResultItemDetails :data="data" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { ref } from "vue"
import { NModal, NButton } from "naive-ui"
import type { ScaPolicyResult } from "@/types/agents"
import ScaResultItemDetails from "./ScaResultItemDetails.vue"

const { data, embedded } = defineProps<{
	data: ScaPolicyResult
	embedded?: boolean
}>()

const DetailsIcon = "carbon:settings-adjust"
const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.sca-result-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

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

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
