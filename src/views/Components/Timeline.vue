<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Timeline</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/timeline"
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
				<n-timeline>
					<n-timeline-item content="Oops" />
					<n-timeline-item type="success" title="Success" content="success content" time="2023-04-03 20:46" />
					<n-timeline-item type="error" content="Error content" time="2023-04-03 20:46" />
					<n-timeline-item type="warning" title="Warning" content="warning content" time="2023-04-03 20:46" />
					<n-timeline-item
						type="info"
						title="Info"
						content="info content"
						time="2023-04-03 20:46"
						line-type="dashed"
					/>
					<n-timeline-item content="Oops" />
				</n-timeline>
				<template #code="{ html }">
					{{ html(`
					<n-timeline>
						<n-timeline-item content="Oops" />
						<n-timeline-item
							type="success"
							title="Success"
							content="success content"
							time="2023-04-03 20:46"
						/>
						<n-timeline-item type="error" content="Error content" time="2023-04-03 20:46" />
						<n-timeline-item
							type="warning"
							title="Warning"
							content="warning content"
							time="2023-04-03 20:46"
						/>
						<n-timeline-item
							type="info"
							title="Info"
							content="info content"
							time="2023-04-03 20:46"
							line-type="dashed"
						/>
						<n-timeline-item content="Oops" />
					</n-timeline>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Horizontal">
				<div style="overflow: auto">
					<n-timeline horizontal>
						<n-timeline-item content="Oops" />
						<n-timeline-item
							type="success"
							title="Success"
							content="Success content"
							time="2023-04-03 20:46"
						/>
						<n-timeline-item type="error" content="Error content" time="2023-04-03 20:46" />
						<n-timeline-item
							type="warning"
							title="Warning"
							content="Warning content"
							time="2023-04-03 20:46"
						/>
						<n-timeline-item type="info" title="Info" content="Info content" time="2023-04-03 20:46" />
					</n-timeline>
				</div>
				<template #code="{ html }">
					{{ html(`
					<div style="overflow: auto">
						<n-timeline horizontal>
							<n-timeline-item content="Oops" />
							<n-timeline-item
								type="success"
								title="Success"
								content="Success content"
								time="2023-04-03 20:46"
							/>
							<n-timeline-item type="error" content="Error content" time="2023-04-03 20:46" />
							<n-timeline-item
								type="warning"
								title="Warning"
								content="Warning content"
								time="2023-04-03 20:46"
							/>
							<n-timeline-item type="info" title="Info" content="Info content" time="2023-04-03 20:46" />
						</n-timeline>
					</div>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NTimeline, NTimelineItem } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
