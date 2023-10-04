<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Typography</div>
		</div>

		<div class="font-family-section flex justify-between gap-5 mt-8">
			<n-card size="large">
				<div class="ff-display flex flex-col h-full">
					<div class="title">Lexend</div>
					<div class="variants flex gap-5">
						<div class="regular">Regular</div>
						<div class="medium">Medium</div>
						<div class="bold">Bold</div>
					</div>
					<div class="demo">
						“Lorem ipsum dolor sit amet consectetur adipiscing elit at erat consectetur ultricies sapien
						facilisi euismod duis mauris a sed quam aliquet dui eros sit lacus vitae ut viverra a”
					</div>
					<div class="footer flex justify-end grow items-end">
						<n-button tag="a" href="https://fontsource.org/fonts/lexend" target="_blank" type="primary">
							Download font
						</n-button>
					</div>
				</div>
			</n-card>
			<n-card size="large">
				<div class="ff-base flex flex-col h-full">
					<div class="title">Public Sans</div>
					<div class="variants flex gap-5">
						<div class="regular">Regular</div>
						<div class="medium">Medium</div>
						<div class="bold">Bold</div>
					</div>
					<div class="demo">
						“Lorem ipsum dolor sit amet consectetur adipiscing elit at erat consectetur ultricies sapien
						facilisi euismod duis mauris a sed quam aliquet dui eros sit lacus vitae ut viverra a”
					</div>
					<div class="footer flex justify-end grow items-end">
						<n-button
							tag="a"
							href="https://fontsource.org/fonts/public-sans"
							target="_blank"
							type="primary"
						>
							Download font
						</n-button>
					</div>
				</div>
			</n-card>
			<n-card size="large">
				<div class="ff-mono flex flex-col h-full">
					<div class="title">JetBrains Mono</div>
					<div class="variants flex gap-5">
						<div class="regular">Regular</div>
						<div class="medium">Medium</div>
						<div class="bold">Bold</div>
					</div>
					<div class="demo">
						“Lorem ipsum dolor sit amet consectetur adipiscing elit at erat consectetur ultricies sapien
						facilisi euismod duis mauris a sed quam aliquet dui eros sit lacus vitae ut viverra a”
					</div>
					<div class="footer flex justify-end grow items-end">
						<n-button
							tag="a"
							href="https://fontsource.org/fonts/jetbrains-mono"
							target="_blank"
							type="primary"
						>
							Download font
						</n-button>
					</div>
				</div>
			</n-card>
		</div>
		<div class="list-section mt-5">
			<n-card>
				<n-scrollbar x-scrollable style="max-width: 100%">
					<table>
						<thead>
							<tr>
								<th>tag</th>
								<th>family</th>
								<th>size</th>
								<th>weight</th>
								<th>letter spacing</th>
								<th>example</th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td>h1</td>
								<td>Lexend</td>
								<td>30px</td>
								<td>700</td>
								<td>-0.025em</td>
								<td>
									<h1>Heading 1</h1>
								</td>
							</tr>
							<tr>
								<td>h2</td>
								<td>Lexend</td>
								<td>26px</td>
								<td>700</td>
								<td>-0.025em</td>
								<td>
									<h2>Heading 2</h2>
								</td>
							</tr>
							<tr>
								<td>h3</td>
								<td>Lexend</td>
								<td>22px</td>
								<td>700</td>
								<td>-0.025em</td>
								<td>
									<h3>Heading 3</h3>
								</td>
							</tr>
							<tr>
								<td>h4</td>
								<td>Lexend</td>
								<td>18px</td>
								<td>500</td>
								<td>-0.025em</td>
								<td>
									<h4>Heading 4</h4>
								</td>
							</tr>
							<tr>
								<td>h5</td>
								<td>Lexend</td>
								<td>14px</td>
								<td>700</td>
								<td>-0.025em</td>
								<td>
									<h5>Heading 5</h5>
								</td>
							</tr>
							<tr>
								<td>h6</td>
								<td>Public Sans</td>
								<td>12px</td>
								<td>500</td>
								<td>normal</td>
								<td>
									<h6>Heading 6</h6>
								</td>
							</tr>
							<tr>
								<td>p</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit.</p>
								</td>
							</tr>
							<tr>
								<td>code</td>
								<td>JetBrains Mono</td>
								<td>13px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<code>import { ref } from "vue"</code>
								</td>
							</tr>
							<tr>
								<td>blockquote</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<blockquote>
										<p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit.</p>
										<small>Lorem ipsum, Lorem ipsum</small>
									</blockquote>
								</td>
							</tr>
							<tr>
								<td>dl, dt, dd</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400 / 700</td>
								<td>normal</td>
								<td>
									<dl>
										<dt>Definition term</dt>
										<dd>This is the definition description</dd>
										<dt>Another definition term</dt>
										<dd>This is another definition description</dd>
									</dl>
								</td>
							</tr>
							<tr>
								<td>ul, li</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<ul>
										<li>List Item</li>
										<li>
											List Item
											<ul>
												<li>List Item</li>
											</ul>
										</li>
									</ul>
								</td>
							</tr>
							<tr>
								<td>ol, li</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<ol>
										<li>List Item</li>
										<li>
											List Item
											<ol>
												<li>List Item</li>
											</ol>
										</li>
									</ol>
								</td>
							</tr>
							<tr>
								<td>a</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<a>link</a>
								</td>
							</tr>
							<tr>
								<td>abbr</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									<abbr title="HyperText Markup Language">HTML</abbr>
								</td>
							</tr>
							<tr>
								<td>s</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									a
									<s>strike-through</s>
									text
								</td>
							</tr>
							<tr>
								<td>u</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									an
									<u>underlined</u>
									text
								</td>
							</tr>
							<tr>
								<td>small</td>
								<td>Public Sans</td>
								<td>80% / 12px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									a
									<small>small</small>
									text
								</td>
							</tr>
							<tr>
								<td>strong</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>700 / bolder</td>
								<td>normal</td>
								<td>
									a
									<strong>strong</strong>
									text
								</td>
							</tr>
							<tr>
								<td>em</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									an
									<em>italic</em>
									text
								</td>
							</tr>
							<tr>
								<td>sup</td>
								<td>Public Sans</td>
								<td>75% / 11px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									a
									<sup>super</sup>
									text
								</td>
							</tr>
							<tr>
								<td>sub</td>
								<td>Public Sans</td>
								<td>75% / 11px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									a
									<sub>sub</sub>
									text
								</td>
							</tr>
							<tr>
								<td>mark</td>
								<td>Public Sans</td>
								<td>15px</td>
								<td>400</td>
								<td>normal</td>
								<td>
									a
									<mark>highlighted</mark>
									text
								</td>
							</tr>
						</tbody>
					</table>
				</n-scrollbar>
			</n-card>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NCard, NButton, NScrollbar } from "naive-ui"
</script>

<style lang="scss" scoped>
.page {
	container-type: inline-size;

	.font-family-section {
		.n-card {
			.title {
				font-size: 30px;
				font-weight: 700;
				margin-bottom: 16px;
			}
			.variants {
				color: var(--primary-color);
				margin-bottom: 16px;

				.regular {
					font-weight: 400;
				}
				.medium {
					font-weight: 500;
				}
				.bold {
					font-weight: 700;
				}
			}
			.demo {
				margin-bottom: 20px;
				color: var(--fg-secondary-color);
			}

			.ff-display {
				.title,
				.variants,
				.demo {
					font-family: var(--font-family-display);
				}
			}

			.ff-base {
				.title,
				.variants,
				.demo {
					font-family: var(--font-family);
				}
			}

			.ff-mono {
				.title,
				.variants,
				.demo {
					font-family: var(--font-family-mono);
				}
			}
		}

		@container (max-width: 900px) {
			flex-direction: column;
		}
	}
	.list-section {
		table {
			width: 100%;
			min-width: 400px;

			th,
			td {
				text-align: left;
				padding: 15px 10px;
				border-bottom: 1px dashed var(--border-color);

				&:first-child {
					width: 100px;
				}
				&:last-child {
					width: 300px;
				}
			}

			th {
				white-space: nowrap;
				text-transform: uppercase;
				color: var(--fg-secondary-color);
			}

			tr {
				td {
					&:not(:last-child) {
						white-space: nowrap;
					}
				}
			}
		}

		@container (max-width: 900px) {
			table {
				th,
				td {
					&:not(:first-child):not(:last-child) {
						display: none;
					}
				}
			}
		}
	}
}
</style>
