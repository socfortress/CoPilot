<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Icons</div>
		</div>
		<div class="main">
			<strong>Pinx</strong>
			uses the
			<a href="https://iconify.design/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">iconify</a>
			library which gives the possibility to integrate, many icon sets. You can find
			<a href="https://icones.js.org/">here</a>
			all sets available. Here, instead, are some examples:

			<div class="groups grid gap-5 mt-8">
				<n-card class="group" title="Carbon">
					<div class="list">
						<div v-for="icon of Carbon" :key="icon" class="icon-box">
							<Icon :size="20" :name="icon"></Icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button tag="a" href="https://iconify.design/" target="_blank" type="primary" alt="docs">
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Flags">
					<div class="list">
						<div v-for="icon of Flags" :key="icon" class="icon-box">
							<Icon :size="20" :name="icon"></Icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button tag="a" href="https://iconify.design/" target="_blank" type="primary" alt="docs">
								See more
							</n-button>
						</div>
					</template>
				</n-card>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NCard, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const Carbon = [
	"carbon:3d-cursor",
	"carbon:accessibility-alt",
	"carbon:audio-console",
	"carbon:bicycle",
	"carbon:business-processes",
	"carbon:basketball",
	"carbon:chart-histogram",
	"carbon:cloud-satellite-config",
	"carbon:content-delivery-network",
	"carbon:dashboard",
	"carbon:corn",
	"carbon:cube-view",
	"carbon:data-categorical",
	"carbon:data-volume",
	"carbon:decision-tree",
	"carbon:debug",
	"carbon:delivery-add",
	"carbon:cut-out",
	"carbon:cyclist",
	"carbon:earth-filled",
	"carbon:directory-domain",
	"carbon:direct-link",
	"carbon:fish",
	"carbon:forecast-hail-30"
]
const Flags = [
	"circle-flags:it",
	"circle-flags:ca",
	"circle-flags:br",
	"circle-flags:us",
	"circle-flags:jp",
	"circle-flags:uk",
	"circle-flags:be",
	"circle-flags:fr-cp",
	"circle-flags:cg",
	"circle-flags:fi",
	"circle-flags:in-mn",
	"circle-flags:be",
	"circle-flags:gr",
	"circle-flags:kw",
	"circle-flags:at",
	"circle-flags:ch",
	"circle-flags:sy",
	"circle-flags:ml",
	"circle-flags:hu",
	"circle-flags:de",
	"circle-flags:fx",
	"circle-flags:kr",
	"circle-flags:es-variant",
	"circle-flags:cz"
]
</script>

<style lang="scss" scoped>
.page {
	.main {
		.groups {
			grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));

			@media (max-width: 450px) {
				grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
			}
			.group {
				.list {
					margin-top: 10px;
					display: grid;
					gap: 12px;
					align-items: start;
					grid-template-columns: repeat(auto-fit, minmax(45px, 1fr));

					.icon-box {
						background-color: var(--bg-secondary-color);
						border-radius: 10px;
						aspect-ratio: 1;
						display: flex;
						align-items: center;
						justify-content: center;
					}
				}
			}
		}
	}
}
</style>
