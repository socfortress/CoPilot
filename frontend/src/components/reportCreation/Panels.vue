<template>
	<div class="report-panels">
		isDirty:{{ isDirty }},{{ linksList.length }}
		<div class="panels-container grid grid-cols-2 gap-6" :class="{ printing }">
			<div class="panel" v-for="panel of linksList" :key="panel.panel_id">
				<iframe :src="panel.panel_url + '&theme=light'" v-show="panelTheme === 'light'"></iframe>
				<iframe :src="panel.panel_url + '&theme=dark'" v-show="panelTheme === 'dark'"></iframe>
			</div>
		</div>

		<div class="toolbar">
			<n-button type="success" v-if="linksList.length" @click="print()">
				<template #icon>
					<Icon :name="PrintIcon"></Icon>
				</template>
				Print Report
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import type { PanelLink } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import { ref, nextTick } from "vue"
// import html2canvas from "html2canvas"
// @ts-ignore
// import domtoimage from "dom-to-image-more"

const isDirty = defineModel<boolean>("isDirty", { default: false })
const printing = ref(false)
const panelTheme = ref<"light" | "dark">("light")

const { linksList } = defineProps<{
	linksList: PanelLink[]
}>()

const PrintIcon = "carbon:printer"

function print() {
	printing.value = true
	// panelTheme.value = "light"

	nextTick(() => {
		setTimeout(() => {
			window.print()
			// panelTheme.value = "dark"
			printing.value = false
		}, 2000)
	})

	/*
	// @ts-ignore
	html2canvas(document.querySelector(".page"), { allowTaint: true, useCORS: true }).then(canvas => {
		//document.body.appendChild(canvas)
		console.log(canvas.toDataURL("image/jpeg", 0.9))
	})
	var node = document.querySelector(".page")

	domtoimage
		.toPng(node)
		// @ts-ignore
		.then(function (dataUrl) {
			var img = new Image()
			img.src = dataUrl
			console.log(dataUrl)
			document.body.appendChild(img)
		})
		// @ts-ignore
		.catch(function (error) {
			console.error("oops, something went wrong!", error)
		})
		*/
}
</script>

<style lang="scss" scoped>
.report-panels {
	.panels-container {
		.panel {
			iframe {
				width: 100%;
				height: 500px;
			}
		}

		&.printing {
			grid-template-columns: repeat(1, minmax(0, 1fr));
			max-width: 600px;
		}
	}
}
</style>

<style lang="scss">
@media print {
	html,
	body {
		overflow: initial;
	}
	body {
		#app {
			height: initial;
			background-color: white;

			& > .n-config-provider {
				& > .layout {
					display: block;
					height: initial;
					background-color: white;

					& > .header-bar {
						display: none;
					}
					& > .main {
						background-color: white;
						overflow: initial;
						height: initial;

						header.toolbar {
							display: none;
						}
						footer.footer {
							display: none;
						}

						& > .n-scrollbar {
							overflow: initial;
							height: initial;

							& > .n-scrollbar-container {
								overflow: initial;
								height: initial;
							}
						}

						.page {
							.report-wizard {
								display: none;
							}
							.report-panels {
								max-width: 600px;

								.panels-container {
									grid-template-columns: repeat(1, minmax(0, 1fr));

									.panel {
										border: 2px solid black;
									}
								}
								.toolbar {
									display: none;
								}
							}
						}
					}
				}
			}
		}
	}
}
</style>
