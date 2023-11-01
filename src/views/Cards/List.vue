<template>
	<div class="page">
		<div class="list">
			<div class="masonry">
				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload">
						<template #default>
							<DemoList minWidth="400px" />
						</template>
						<template #footer>
							<DemoChart type="bar" data-type="months" :highlight="true" />
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload" :show-image="true" hideSubtitle>
						<template #default>
							<DemoList minWidth="400px" :percentage="{ useBackground: true, icon: 'arrow' }" />
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions
						:expand="expand"
						:isExpand="isExpand"
						:reload="reload"
						:segmented="true"
						:hideSubtitle="true"
					>
						<template #default>
							<DemoList
								minWidth="400px"
								:image="true"
								:hide-value="true"
								:percentage="{ progress: 'circle', icon: 'operator', useColor: true }"
							/>
						</template>
						<template #action>
							<DemoChart
								type="area"
								data-type="years-10"
								class="!mb-4"
								:strokeWidth="3"
								:fontColor="textSecondaryColor"
							/>
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions
						:expand="expand"
						:isExpand="isExpand"
						:reload="reload"
						:segmented="true"
						:hideSubtitle="true"
					>
						<template #default>
							<DemoList minWidth="400px" :dataType="'airline'" :percentage="{ hide: true }" />
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload">
						<template #default>
							<DemoList
								minWidth="400px"
								:dataType="'airline'"
								:image="true"
								:hideValue="true"
								:hideSubtitle="true"
								:percentage="{ useColor: true, icon: 'operator', progress: 'line' }"
							/>
						</template>
						<template #action>
							<div class="p-5 flex justify-end">
								<n-button type="primary">Full report</n-button>
							</div>
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload">
						<template #default>
							<DemoList
								minWidth="400px"
								:hideValue="true"
								:hideSubtitle="true"
								:percentage="{ icon: 'arrow', useOpacity: true, progress: 'line' }"
							/>
						</template>
						<template #footer>
							<DemoChart
								type="bar"
								data-type="week"
								:colorsSecondary="true"
								:fontColor="textSecondaryColor"
							/>
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions
						:expand="expand"
						:isExpand="isExpand"
						:reload="reload"
						:segmented="true"
						:hideSubtitle="true"
					>
						<template #default>
							<DemoList
								minWidth="400px"
								:dataType="'airline'"
								:image="true"
								:hideValue="true"
								:hideSubtitle="true"
								:percentage="{ useColor: false, useOpacity: true, icon: 'operator' }"
							/>
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload">
						<template #default>
							<DemoList
								minWidth="400px"
								:hideValue="true"
								:hideSubtitle="true"
								:percentage="{ useBackground: true, icon: 'operator' }"
							/>
						</template>
					</CardActions>
				</CardWrapper>

				<CardWrapper v-slot="{ expand, isExpand, reload }">
					<CardActions :expand="expand" :isExpand="isExpand" :reload="reload">
						<template #default>
							<DemoList
								minWidth="400px"
								:dataType="'airline'"
								:hideSubtitle="true"
								:percentage="{ hide: true }"
							/>
						</template>
						<template #action>
							<DemoChart
								type="bar"
								data-type="months"
								:highlight="true"
								:color="textColor"
								class="pb-3 pt-2"
							/>
						</template>
					</CardActions>
				</CardWrapper>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { computed } from "vue"
import DemoChart from "@/components/charts/DemoApex.vue"
import DemoList from "@/components/list/List.vue"
import { useThemeStore } from "@/stores/theme"

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const textColor = computed<string>(() => style.value["--fg-color"])
const textSecondaryColor = computed<string>(() => style.value["--fg-secondary-color"])
</script>

<style lang="scss" scoped>
.page {
	.list {
		container-type: inline-size;

		.masonry {
			--notes-gap: 1.25em;
			column-count: 3;
			column-gap: var(--notes-gap);

			@container (max-width: 1500px) {
				column-count: 2;
			}

			@container (max-width: 1080px) {
				column-count: 1;
			}

			.card-wrapper {
				overflow: hidden;
				margin-bottom: var(--notes-gap);
			}
		}
	}
}
</style>
