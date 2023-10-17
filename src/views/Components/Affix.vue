<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Affix</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/affix"
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
				<template #dscription>
					Affix can be
					<n-text code>absolute</n-text>
					or
					<n-text code>fixed</n-text>
					positioned. You may need some css tricks to make it works as following. By default position is set
					to fixed, because in most cases scrolled element is
					<n-text code>document</n-text>
					.
				</template>
				<div class="absolute-anchor-container">
					<div ref="containerRef" class="anchor-container">
						<div class="padding" />
						<div class="content">
							<div style="display: inline-block; width: 50%" v-if="containerRef">
								<n-affix :trigger-top="50" :position="'absolute'" :listen-to="containerRef">
									<n-tag>Affix Trigger Top 50px</n-tag>
								</n-affix>
							</div>
							<div style="display: inline-block; width: 50%">
								<n-affix :trigger-bottom="60" :position="'absolute'" :listen-to="containerRef">
									<n-tag>Affix Trigger Bottom 60px</n-tag>
								</n-affix>
							</div>
						</div>
					</div>
				</div>
				<template #code="{ html, css }">
					{{ html(`
					<div class="absolute-anchor-container">
						<div ref="containerRef" class="container">
							<div class="padding" />
							<div class="content">
								<div style="display: inline-block; width: 50%">
									<n-affix :trigger-top="50" position="absolute" :listen-to="containerRef">
										<n-tag>Affix Trigger Top 50px</n-tag>
									</n-affix>
								</div>
								<div style="display: inline-block; width: 50%">
									<n-affix :trigger-bottom="60" position="absolute" :listen-to="containerRef">
										<n-tag>Affix Trigger Bottom 60px</n-tag>
									</n-affix>
								</div>
							</div>
						</div>
					</div>
					`) }}

					{{
						css(`
						.absolute-anchor-container {
							width: 100%;
							height: 200px;
							position: relative;
						}
						
						.anchor-container {
							height: 200px;
							background-color: rgba(128, 128, 128, 0.3);
							border-radius: 3px;
							overflow: auto;
						}
						
						.padding {
							height: 150px;
							width: 100%;
							background-color: rgba(128, 128, 128, 0.15);
						}
						
						.content {
							height: 600px;
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NAffix, NText, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const containerRef = ref<HTMLElement | undefined>(undefined)
</script>

<style scoped>
.absolute-anchor-container {
	width: 100%;
	height: 200px;
	position: relative;
}

.anchor-container {
	height: 200px;
	background-color: rgba(128, 128, 128, 0.3);
	border-radius: 3px;
	overflow: auto;
}

.padding {
	height: 150px;
	width: 100%;
	background-color: rgba(128, 128, 128, 0.15);
}

.content {
	height: 600px;
}
</style>
