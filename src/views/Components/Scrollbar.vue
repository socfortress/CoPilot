<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Scrollbar</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/scrollbar"
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
				<n-scrollbar style="max-height: 120px">
					And as I sat there, brooding on the old unknown world, I thought of Gatsby’s wonder when he first
					picked out the green light at the end of Daisy’s dock. He had come a long way to this blue lawn and
					his dream must have seemed so close that he could hardly fail to grasp it. He did not know that it
					was already behind him, somewhere back in that vast obscurity beyond the city, where the dark fields
					of the republic rolled on under the night.
					<br />
					<br />

					Gatsby believed in the green light, the orgastic future that year by year recedes before us. It
					eluded us then, but that’s no matter—tomorrow we will run faster, stretch out our arms farther. . .
					. And one fine morning——
					<br />
					<br />

					So we beat on, boats against the current, borne back ceaselessly into the past.
				</n-scrollbar>
				<template #code="{ html }">
					{{ html(`
					<n-scrollbar style="max-height: 120px">
						And as I sat there, brooding on the old unknown world, I thought of Gatsby’s wonder when he
						first picked out the green light at the end of Daisy’s dock. He had come a long way to this blue
						lawn and his dream must have seemed so close that he could hardly fail to grasp it. He did not
						know that it was already behind him, somewhere back in that vast obscurity beyond the city,
						where the dark fields of the republic rolled on under the night.
						<br />
						<br />

						Gatsby believed in the green light, the orgastic future that year by year recedes before us. It
						eluded us then, but that’s no matter—tomorrow we will run faster, stretch out our arms farther.
						. . . And one fine morning——
						<br />
						<br />

						So we beat on, boats against the current, borne back ceaselessly into the past.
					</n-scrollbar>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Scroll horizontally">
				<n-scrollbar x-scrollable>
					<div style="white-space: nowrap; padding: 12px">
						And as I sat there, brooding on the old unknown world, I thought of Gatsby’s wonder when he
						first picked out the green light at the end of Daisy’s dock. He had come a long way to this blue
						lawn and his dream must have seemed so close that he could hardly fail to grasp it. He did not
						know that it was already behind him, somewhere back in that vast obscurity beyond the city,
						where the dark fields of the republic rolled on under the night. Gatsby believed in the green
						light, the orgastic future that year by year recedes before us. It eluded us then, but that’s no
						matter—tomorrow we will run faster, stretch out our arms farther. . . . And one fine morning——
						So we beat on, boats against the current, borne back ceaselessly into the past.
					</div>
				</n-scrollbar>
				<template #code="{ html }">
					{{ html(`
					<n-scrollbar x-scrollable>
						<div style="white-space: nowrap; padding: 12px">
							And as I sat there, brooding on the old unknown world, I thought of Gatsby’s wonder when he
							first picked out the green light at the end of Daisy’s dock. He had come a long way to this
							blue lawn and his dream must have seemed so close that he could hardly fail to grasp it. He
							did not know that it was already behind him, somewhere back in that vast obscurity beyond
							the city, where the dark fields of the republic rolled on under the night. Gatsby believed
							in the green light, the orgastic future that year by year recedes before us. It eluded us
							then, but that’s no matter—tomorrow we will run faster, stretch out our arms farther. . . .
							And one fine morning—— So we beat on, boats against the current, borne back ceaselessly into
							the past.
						</div>
					</n-scrollbar>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
