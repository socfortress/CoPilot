<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Popover</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/popover"
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
			<CardCodeExample title="Basic">
				<n-space>
					<n-popover trigger="hover">
						<template #trigger>
							<n-button>Hover</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-popover>
					<n-popover trigger="hover" :keep-alive-on-hover="false">
						<template #trigger>
							<n-button>Hover (ignore popup)</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-popover>
					<n-popover trigger="click">
						<template #trigger>
							<n-button>Click</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-popover>
					<n-popover trigger="focus">
						<template #trigger>
							<n-button>Focus</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-popover>
					<n-popover trigger="manual" :show="showPopover">
						<template #trigger>
							<n-button @click="showPopover = !showPopover">Manual</n-button>
						</template>
						<span>I wish they all could be California girls</span>
					</n-popover>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-popover trigger="hover">
							<template #trigger>
								<n-button>Hover</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-popover>
						<n-popover trigger="hover" :keep-alive-on-hover="false">
							<template #trigger>
								<n-button>Hover (ignore popup)</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-popover>
						<n-popover trigger="click">
							<template #trigger>
								<n-button>Click</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-popover>
						<n-popover trigger="focus">
							<template #trigger>
								<n-button>Focus</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-popover>
						<n-popover trigger="manual" :show="showPopover">
							<template #trigger>
								<n-button @click="showPopover = !showPopover">Manual</n-button>
							</template>
							<span>I wish they all could be California girls</span>
						</n-popover>
					</n-space>
					`) }}

					{{
						js(`
						const showPopover = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Placement">
				<n-switch v-model:value="overlap" />
				Overlap Trigger Element
				<n-divider />
				<div class="popover-grid">
					<n-popover :overlap="overlap" placement="top-start" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 1 / 1 / 2 / 2">Top Start</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="top" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 1 / 2 / 2 / 3">Top</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="top-end" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 1 / 3 / 2 / 4">Top End</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="left-start" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 2 / 1 / 3 / 2">Left Start</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="left" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 3 / 1 / 4 / 2">Left</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="left-end" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 4 / 1 / 5 / 2">Left End</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="right-start" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 2 / 3 / 3 / 4">Right Start</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="right" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 3 / 3 / 4 / 4">Right</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="right-end" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 4 / 3 / 5 / 4">Right End</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="bottom-start" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 5 / 1 / 6 / 2">Bottom Start</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="bottom" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 5 / 2 / 6 / 3">Bottom</n-button>
						</template>
						<div class="large-text">Oops!</div>
					</n-popover>
					<n-popover :overlap="overlap" placement="bottom-end" trigger="click">
						<template #trigger>
							<n-button size="small" style="grid-area: 5 / 3 / 6 / 4">Bottom End</n-button>
						</template>
						<div class="large-text">Oops</div>
					</n-popover>
				</div>
				<template #code="{ html, js, css }">
					{{ html(`
					<n-switch v-model:value="overlap" />
					Overlap Trigger Element
					<n-divider />
					<div class="popover-grid">
						<n-popover :overlap="overlap" placement="top-start" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 1 / 1 / 2 / 2">Top Start</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="top" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 1 / 2 / 2 / 3">Top</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="top-end" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 1 / 3 / 2 / 4">Top End</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="left-start" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 2 / 1 / 3 / 2">Left Start</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="left" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 3 / 1 / 4 / 2">Left</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="left-end" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 4 / 1 / 5 / 2">Left End</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="right-start" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 2 / 3 / 3 / 4">Right Start</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="right" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 3 / 3 / 4 / 4">Right</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="right-end" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 4 / 3 / 5 / 4">Right End</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="bottom-start" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 5 / 1 / 6 / 2">Bottom Start</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="bottom" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 5 / 2 / 6 / 3">Bottom</n-button>
							</template>
							<div class="large-text">Oops!</div>
						</n-popover>
						<n-popover :overlap="overlap" placement="bottom-end" trigger="click">
							<template #trigger>
								<n-button size="small" style="grid-area: 5 / 3 / 6 / 4">Bottom End</n-button>
							</template>
							<div class="large-text">Oops</div>
						</n-popover>
					</div>
					`) }}

					{{
						js(`
						const overlap = ref(false)
						`)
					}}

					{{
						css(`
						.popover-grid {
							display: grid;
							grid-template-columns: auto auto auto auto auto;
							grid-gap: 12px;
							justify-content: center;
							align-items: center;
						}
						.large-text {
							font-size: 48px;
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NPopover, NButton, NDivider, NSwitch } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const showPopover = ref(false)

const overlap = ref(false)
</script>

<style scoped>
.popover-grid {
	display: grid;
	grid-template-columns: auto auto auto auto auto;
	grid-gap: 12px;
	justify-content: center;
	align-items: center;
}

.large-text {
	font-size: 48px;
}
</style>
