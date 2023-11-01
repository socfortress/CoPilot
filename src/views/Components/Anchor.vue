<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Anchor</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/anchor"
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
				<n-space style="margin-bottom: 12px">
					<n-switch v-model:value="showRail" />
					Show Rail
					<n-switch v-model:value="showBackground" />
					Show Background
				</n-space>
				<n-anchor :show-rail="showRail" :show-background="showBackground">
					<n-anchor-link title="Demos" href="#Demos">
						<n-anchor-link title="Basic" href="#basic.vue" />
						<n-anchor-link title="Ignore-Gap" href="#ignore-gap.vue" />
						<n-anchor-link title="Affix" href="#affix.vue" />
						<n-anchor-link title="Scroll To" href="#scrollto.vue" />
					</n-anchor-link>
					<n-anchor-link title="API" href="#API" />
				</n-anchor>
				<template #code="{ html, js }">
					{{ html(`
					<n-space style="margin-bottom: 12px">
						<n-switch v-model:value="showRail" />
						Show Rail
						<n-switch v-model:value="showBackground" />
						Show Background
					</n-space>
					<n-anchor :show-rail="showRail" :show-background="showBackground">
						<n-anchor-link title="Demos" href="#Demos">
							<n-anchor-link title="Basic" href="#basic.vue" />
							<n-anchor-link title="Ignore-Gap" href="#ignore-gap.vue" />
							<n-anchor-link title="Affix" href="#affix.vue" />
							<n-anchor-link title="Scroll To" href="#scrollto.vue" />
						</n-anchor-link>
						<n-anchor-link title="API" href="#API" />
					</n-anchor>
					`) }}

					{{
						js(`
						const showRail = ref(true)
						const showBackground = ref(true)
					`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NSwitch, NAnchor, NAnchorLink } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const showRail = ref(true)
const showBackground = ref(true)
</script>
