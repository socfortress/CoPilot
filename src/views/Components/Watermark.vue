<template>
	<div class="page page-wrapped">
		<n-scrollbar style="max-height: 100%">
			<div class="page-header">
				<div class="title">Watermark</div>
				<div class="links">
					<a
						href="https://www.naiveui.com/en-US/light/components/watermark"
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
					<n-watermark
						content="Watermark"
						cross
						selectable
						:font-size="16"
						:line-height="16"
						:width="192"
						:height="128"
						:x-offset="12"
						:y-offset="28"
						:rotate="-15"
					>
						<n-table :bordered="false" :single-line="false">
							<thead>
								<tr>
									<th>...</th>
									<th>...</th>
									<th>...</th>
									<th>...</th>
									<th>...</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td>...</td>
									<td>...</td>
									<td>...</td>
									<td>...</td>
									<td>...</td>
								</tr>
								<tr>
									<td>...</td>
									<td>...</td>
									<td>...</td>
									<td>...</td>
									<td>...</td>
								</tr>
							</tbody>
						</n-table>
					</n-watermark>
					<template #code="{ html }">
						{{ html(`
						<n-watermark
							content="Watermark"
							cross
							selectable
							:font-size="16"
							:line-height="16"
							:width="192"
							:height="128"
							:x-offset="12"
							:y-offset="28"
							:rotate="-15"
						>
							<n-table :bordered="false" :single-line="false">
								<thead>
									<tr>
										<th>...</th>
										<th>...</th>
										<th>...</th>
										<th>...</th>
										<th>...</th>
									</tr>
								</thead>
								<tbody>
									<tr>
										<td>...</td>
										<td>...</td>
										<td>...</td>
										<td>...</td>
										<td>...</td>
									</tr>
									<tr>
										<td>...</td>
										<td>...</td>
										<td>...</td>
										<td>...</td>
										<td>...</td>
									</tr>
								</tbody>
							</n-table>
						</n-watermark>
						`) }}
					</template>
				</CardCodeExample>

				<CardCodeExample title="Fullscreen">
					<template #description>You can make it displayed in fullscreen mode.</template>
					<n-watermark
						v-if="show"
						content="All the roads we have to walk are winding"
						cross
						fullscreen
						:font-size="16"
						:line-height="16"
						:width="384"
						:height="384"
						:x-offset="12"
						:y-offset="80"
						:rotate="-15"
					/>
					<n-switch v-model:value="show" />
					<template #code="{ html, js }">
						{{ html(`
						<n-watermark
							v-if="show"
							content="All the roads we have to walk are winding"
							cross
							fullscreen
							:font-size="16"
							:line-height="16"
							:width="384"
							:height="384"
							:x-offset="12"
							:y-offset="80"
							:rotate="-15"
						/>
						<n-switch v-model:value="show" />
						`) }}

						{{
							js(`
						const show = ref(false)
						`)
						}}
					</template>
				</CardCodeExample>
			</div>
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { NWatermark, NTable, NSwitch, NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const show = ref(false)
</script>
