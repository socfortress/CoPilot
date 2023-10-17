<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Google Maps</div>
			<div class="links">
				<a href="https://vue-map.netlify.app/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<n-card>
			<GMapMap :center="center" :zoom="7" map-type-id="terrain" style="width: 100%; height: 60vh">
				<GMapMarker
					:key="index"
					v-for="(m, index) in markers"
					:position="m.position"
					:clickable="true"
					:draggable="true"
					@click="center = m.position"
				/>
			</GMapMap>
		</n-card>
	</div>
</template>
<script setup lang="ts">
import { NCard } from "naive-ui"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const center = ref({ lat: 42.50974755936583, lng: 11.917505449320428 })
const markers = ref([
	{
		position: {
			lat: 42.50974755936583,
			lng: 11.917505449320428
		}
	},
	{
		position: {
			lat: 54.333850327927905,
			lng: 52.78937854256488
		}
	},
	{
		position: {
			lat: 18.01252674640049,
			lng: 13.608381625739803
		}
	},
	{
		position: {
			lat: 47.72166505031789,
			lng: -97.38239022435489
		}
	},
	{
		position: {
			lat: -5.786721981148869,
			lng: -59.851314166681775
		}
	},
	{
		position: {
			lat: 35.83726851258224,
			lng: 138.4458901659339
		}
	},
	{
		position: {
			lat: -25.442451809683316,
			lng: 132.80387723696182
		}
	}
])
</script>
