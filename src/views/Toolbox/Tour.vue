<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Tour</div>
		</div>

		<n-card>
			Using
			<a href="https://shepherdjs.dev/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
				shepherd.js
			</a>
			, you can instantly create beautiful tours that explain the features of your application. Here's an example.

			<div class="demo mt-4">
				<n-button @click="startTour()" type="primary" size="large">Start tour</n-button>
			</div>
		</n-card>
	</div>
</template>

<script lang="ts" setup>
import { NCard, NButton } from "naive-ui"
import { onMounted, computed, watch } from "vue"
import "shepherd.js/dist/css/shepherd.css"
import Shepherd from "shepherd.js"
import { offset } from "@floating-ui/dom"
import "@/assets/scss/shepherd-override.scss"
import { useThemeStore } from "@/stores/theme"

const theme = computed(() => (useThemeStore().isThemeDark ? "s-dark" : "s-light"))

const tour = new Shepherd.Tour({
	useModalOverlay: true,
	defaultStepOptions: {
		cancelIcon: {
			enabled: true
		},
		classes: "styled " + theme.value,
		scrollTo: { behavior: "smooth", block: "center" }
	}
})

function startTour() {
	tour.start()
}

watch(theme, val => {
	if (tour?.steps?.length) {
		for (const step of tour.steps) {
			step.updateStepOptions({
				classes: "styled " + val
			})
		}
	}
})

onMounted(() => {
	tour.addStep({
		title: "Logo",
		text: "Here you can place your application's logo and you can manage 4 variations: <code>logo_dark</code>, <code>logo_light</code>, <code>icon_dark</code>, <code>icon_light</code>, .",
		attachTo: {
			element: window.innerWidth <= 700 ? ".toolbar .logo img" : ".logo img",
			on: "bottom"
		},
		floatingUIOptions: {
			middleware: [offset(12)]
		},
		buttons: [
			{
				action() {
					return this.cancel()
				},
				secondary: true,
				text: "Exit"
			},
			{
				action() {
					return this.next()
				},
				text: "Next"
			}
		]
	})
	if (window.innerWidth > 700) {
		tour.addStep({
			title: "Breadcrumb",
			text: "Thanks to the breadcrumb element you can always indicate the current page to the user in a clear and interactive way.",
			attachTo: {
				element: ".n-breadcrumb-item__link",
				on: "bottom"
			},
			floatingUIOptions: {
				middleware: [offset(14)]
			},
			buttons: [
				{
					action() {
						return this.back()
					},
					secondary: true,
					text: "Back"
				},
				{
					action() {
						return this.next()
					},
					text: "Next"
				}
			]
		})
	}
	if (window.innerWidth > 1500) {
		tour.addStep({
			title: "Latest/Pinned pages",
			text: "With this component, you will be able to display the history of viewed pages and optionally pin any of them to keep them visible at all times.",
			attachTo: {
				element: ".pinned-pages",
				on: "bottom"
			},
			floatingUIOptions: {
				middleware: [offset(14)]
			},
			buttons: [
				{
					action() {
						return this.back()
					},
					secondary: true,
					text: "Back"
				},
				{
					action() {
						return this.next()
					},
					text: "Next"
				}
			]
		})
	}
	tour.addStep({
		title: "Bubble Toolbar",
		text: "In this element, you can insert all the components you want to be consistently visible on all devices.",
		attachTo: {
			element: ".bubble",
			on: "bottom"
		},
		floatingUIOptions: {
			middleware: [offset(16)]
		},
		buttons: [
			{
				action() {
					return this.back()
				},
				secondary: true,
				text: "Back"
			},
			{
				action() {
					return this.next()
				},
				text: "Next"
			}
		]
	})
	tour.addStep({
		title: "Layout Settings",
		text: "This is the tool to modify the way your platform appears. You can perform tests from here to quickly find the right combination.",
		attachTo: {
			element: ".layout-settings",
			on: "left"
		},
		floatingUIOptions: {
			middleware: [offset(16)]
		},
		buttons: [
			{
				action() {
					return this.back()
				},
				secondary: true,
				text: "Back"
			},
			{
				action() {
					return this.next()
				},
				text: "Next"
			}
		]
	})
	tour.addStep({
		title: "Thank you",
		text: `
			Thank you for completing the tour.<br/><br/>
			Check out the <a href="https://shepherdjs.dev/docs/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">documentation</a> to learn more.`,
		buttons: [
			{
				action() {
					return this.back()
				},
				secondary: true,
				text: "Back"
			},
			{
				action() {
					return this.next()
				},
				text: "Done"
			}
		]
	})
})
</script>
