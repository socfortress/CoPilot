<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Tag</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/tag"
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
			<CardCodeExample title="Type">
				<n-space>
					<n-tag>Real Love</n-tag>
					<n-tag type="success">Yes It Is</n-tag>
					<n-tag type="warning">I'm Down</n-tag>
					<n-tag type="error">Yesterday</n-tag>
					<n-tag type="info">I'm Looking Through You</n-tag>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-tag>Real Love</n-tag>
						<n-tag type="success">Yes It Is</n-tag>
						<n-tag type="warning">I'm Down</n-tag>
						<n-tag type="error">Yesterday</n-tag>
						<n-tag type="info">I'm Looking Through You</n-tag>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Closable">
				<n-space>
					<n-tag closable @close="handleClose">Real Love</n-tag>
					<n-tag type="success" closable @close="handleClose">Yes It Is</n-tag>
					<n-tag type="warning" closable @close="handleClose">I'm Down</n-tag>
					<n-tag type="error" closable @close="handleClose">Yesterday</n-tag>
					<n-tag
						type="info"
						closable
						:trigger-click-on-close="false"
						@click="handleClick"
						@close="handleClose"
					>
						I'm Looking Through You
					</n-tag>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-tag closable @close="handleClose">Real Love</n-tag>
						<n-tag type="success" closable @close="handleClose">Yes It Is</n-tag>
						<n-tag type="warning" closable @close="handleClose">I'm Down</n-tag>
						<n-tag type="error" closable @close="handleClose">Yesterday</n-tag>
						<n-tag
							type="info"
							closable
							:trigger-click-on-close="false"
							@click="handleClick"
							@close="handleClose"
						>
							I'm Looking Through You
						</n-tag>
					</n-space>
					`) }}

					{{
						js(`
						const message = useMessage()
						function handleClose() {
							message.info("tag close")
						}
						function handleClick() {
							message.info("tag click")
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Icon">
				<n-space>
					<n-tag type="success">
						Checked
						<template #icon>
							<Icon :name="CheckmarkCircle" />
						</template>
					</n-tag>
					<n-tag round :bordered="false" type="success">
						Checked
						<template #icon>
							<Icon :name="CheckmarkCircle" />
						</template>
					</n-tag>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-tag type="success">
							Checked
							<template #icon>
								<n-icon :component="CheckmarkCircle" />
							</template>
						</n-tag>
						<n-tag round :bordered="false" type="success">
							Checked
							<template #icon>
								<n-icon :component="CheckmarkCircle" />
							</template>
						</n-tag>
					</n-space>
					`) }}

					{{
						js(`
						import { CheckmarkCircle } from '@vicons/ionicons5'
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NTag, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
const CheckmarkCircle = "ion:checkmark-circle"

const message = useMessage()
function handleClose() {
	message.info("tag close")
}
function handleClick() {
	message.info("tag click")
}
</script>
