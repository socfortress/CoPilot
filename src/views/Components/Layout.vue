<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Layout</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/layout"
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
				<n-layout style="height: 360px">
					<n-layout-header style="height: 64px; padding: 24px" bordered>Header</n-layout-header>
					<n-layout position="absolute" style="top: 64px; bottom: 64px" has-sider>
						<n-layout-sider
							content-style="padding: 24px;"
							:native-scrollbar="false"
							bordered
							collapse-mode="width"
							:collapsed-width="120"
							:width="240"
							show-trigger="bar"
						>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
							<n-h2>Handian Bridge</n-h2>
						</n-layout-sider>
						<n-layout content-style="padding: 24px;" :native-scrollbar="false">
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
							<n-h2>Pingshan Road</n-h2>
						</n-layout>
					</n-layout>
					<n-layout-footer position="absolute" style="height: 64px; padding: 24px" bordered>
						Footer
					</n-layout-footer>
				</n-layout>
				<template #code="{ html }">
					{{ html(`
					<n-layout style="height: 360px">
						<n-layout-header style="height: 64px; padding: 24px" bordered>Header</n-layout-header>
						<n-layout position="absolute" style="top: 64px; bottom: 64px" has-sider>
							<n-layout-sider
								content-style="padding: 24px;"
								:native-scrollbar="false"
								bordered
								collapse-mode="width"
								:collapsed-width="120"
								:width="240"
								show-trigger="bar"
							>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
								<n-h2>Handian Bridge</n-h2>
							</n-layout-sider>
							<n-layout content-style="padding: 24px;" :native-scrollbar="false">
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
								<n-h2>Pingshan Road</n-h2>
							</n-layout>
						</n-layout>
						<n-layout-footer position="absolute" style="height: 64px; padding: 24px" bordered>
							Footer
						</n-layout-footer>
					</n-layout>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NLayout, NLayoutHeader, NLayoutSider, NLayoutFooter, NH2 } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
