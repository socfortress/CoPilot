<template>
	<div class="page page-wrapped flex flex-col">
		<div class="page-header">
			<div class="title">RevoGrid</div>
			<div class="links">
				<a
					href="https://revolist.github.io/revogrid/"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="components-list grow">
			<n-card class="card" content-style="padding: 0;">
				<v-grid
					class="grid-component"
					:autoSizeColumn="true"
					:source="source"
					:columns="columns"
					:columnTypes="columnTypes"
					:pinnedTopRows="pinnedTopRows"
					:pinnedBottomRows="pinnedBottomRows"
					:filter="true"
					:theme="theme"
					:resize="true"
					:range="true"
					rowClass="highlighted"
				/>
			</n-card>
		</div>
	</div>
</template>

<script setup lang="js">
import { NIcon, NCard } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { generateFakeDataDemo } from "./grid-assets/dataGenerate"
import people from "./grid-assets/peopleSample"
import VGrid from "@revolist/vue3-datagrid"
import { computed, ref } from "vue"

import PluginNumeral from "@revolist/revogrid-column-numeral"
import PluginDate from "./grid-assets/plugin-date"
import PluginSelect from "./grid-assets/plugin-select"
import { useThemeStore } from "@/stores/theme"

const data = generateFakeDataDemo(people, 50, window.innerWidth > 700)
const dataSource = data.source
const dataColumns = data.columns

const select = new PluginSelect()
const numeric = new PluginNumeral()
const date = new PluginDate()

const columnTypes = ref({
	select,
	numeric,
	date
})

const source = ref(dataSource)
const pinnedBottomRows = ref([])
const columns = ref(dataColumns)
const pinnedTopRows = ref([])

const theme = computed(() => (useThemeStore().isThemeDark ? "darkMaterial" : "material"))
</script>

<style scoped lang="scss">
.page {
	.components-list {
		grid-template-columns: none;

		.card {
			height: 100%;
			width: 100%;
			overflow: hidden;
		}

		:deep() {
			revo-grid {
				height: 100%;
			}

			.temp-bg-range {
				display: initial !important;
			}

			.draggable-wrapper {
				background: #fff;
				color: black;
			}

			revogr-edit {
				background: #fff;
				color: black;
				border: 2px dashed rgba(var(--primary-color-rgb), 0.5);

				input {
					margin: 0px 15px;
					width: calc(100% - 30px);
					height: 100%;
				}
			}

			.bubble {
				color: #fff;
				border: none;
				cursor: default;
				height: 32px;
				display: inline-flex;
				outline: 0;
				padding: 0 10px;
				font-size: 0.8125rem;
				box-sizing: border-box;
				transition:
					background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1) 0ms,
					box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1) 0ms;
				align-items: center;
				white-space: nowrap;
				border-radius: 16px;
				vertical-align: middle;
				justify-content: center;
				text-decoration: none;
				background-color: #e0e0e0;
				opacity: 0.7;
			}
		}
	}
}
</style>
