<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Tooltip</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/tooltip"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-space>
					<n-tooltip placement="top-start" trigger="hover">
						<template #trigger>
							<n-button>Hover</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-tooltip>
					<n-tooltip placement="bottom" trigger="click">
						<template #trigger>
							<n-button>Click</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-tooltip>
					<n-tooltip :show="showPopover" placement="top-end">
						<template #trigger>
							<n-button @click="showPopover = !showPopover">Manual</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-tooltip>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-tooltip placement="top-start" trigger="hover">
							<template #trigger>
								<n-button>Hover</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-tooltip>
						<n-tooltip placement="bottom" trigger="click">
							<template #trigger>
								<n-button>Click</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-tooltip>
						<n-tooltip :show="showPopover" placement="top-end">
							<template #trigger>
								<n-button @click="showPopover = !showPopover">Manual</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-tooltip>
					</n-space>
					`) }}

					{{ js(`const showPopover = ref(false)`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NTooltip, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const showPopover = ref(false)
</script>
