<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Popconfirm</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/popconfirm"
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
				<n-popconfirm @positive-click="handlePositiveClick" @negative-click="handleNegativeClick">
					<template #trigger>
						<n-button>Quote</n-button>
					</template>
					Things pass us by. Nobody can catch them. That's the way we live our lives.
				</n-popconfirm>
				<template #code="{ html, js }">
					{{ html(`
					<n-popconfirm @positive-click="handlePositiveClick" @negative-click="handleNegativeClick">
						<template #trigger>
							<n-button>Quote</n-button>
						</template>
						Things pass us by. Nobody can catch them. That's the way we live our lives.
					</n-popconfirm>
					`) }}

					{{
						js(`
						const message = useMessage()
						function handlePositiveClick() {
							message.info("Yes")
						}
						function handleNegativeClick() {
							message.info("No")
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NPopconfirm, NButton, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const message = useMessage()
function handlePositiveClick() {
	message.info("Yes")
}
function handleNegativeClick() {
	message.info("No")
}
</script>
