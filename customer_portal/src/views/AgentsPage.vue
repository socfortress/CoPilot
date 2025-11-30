<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Agents
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
			<div class="px-4 py-6 sm:px-0">
				<!-- Page Header -->
				<div class="mb-8">
					<h2 class="mb-2 text-2xl font-bold text-gray-900">Agents</h2>
					<p class="text-gray-600">Monitor and manage your organization's security agents</p>
				</div>

				<!-- Loading State -->
				<div v-if="loading" class="flex items-center justify-center py-12">
					<div class="h-12 w-12 animate-spin rounded-full border-b-2 border-indigo-600"></div>
					<span class="ml-3 text-gray-600">Loading agents...</span>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">Error Loading Agents</h3>
							<div class="mt-2 text-sm text-red-700">{{ error }}</div>
							<div class="mt-3">
								<button
									@click="loadAgents"
									class="rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-800 hover:bg-red-200"
								>
									Try Again
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- Content -->
				<div v-else>
					<!-- Stats Summary -->
					<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-4">
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Total Agents</dt>
											<dd class="text-2xl font-semibold text-gray-900">{{ agents.length }}</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-green-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Active Agents</dt>
											<dd class="text-2xl font-semibold text-gray-900">{{ activeAgents }}</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-yellow-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Critical Assets</dt>
											<dd class="text-2xl font-semibold text-gray-900">{{ criticalAgents }}</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-red-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Offline Agents</dt>
											<dd class="text-2xl font-semibold text-gray-900">{{ offlineAgents }}</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Filters -->
					<div class="mb-6 rounded-lg bg-white shadow-sm">
						<div class="border-b border-gray-200 px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900">Filters</h3>
						</div>
						<div class="p-6">
							<div class="grid grid-cols-1 gap-4 md:grid-cols-4">
								<div>
									<label class="mb-2 block text-sm font-medium text-gray-700">Status</label>
									<select
										v-model="filters.status"
										class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
									>
										<option value="">All Statuses</option>
										<option value="active">Active</option>
										<option value="never_connected">Never Connected</option>
										<option value="disconnected">Disconnected</option>
										<option value="pending">Pending</option>
									</select>
								</div>
								<div>
									<label class="mb-2 block text-sm font-medium text-gray-700">Critical Asset</label>
									<select
										v-model="filters.critical"
										class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
									>
										<option value="">All Assets</option>
										<option value="true">Critical Assets</option>
										<option value="false">Regular Assets</option>
									</select>
								</div>
								<div>
									<label class="mb-2 block text-sm font-medium text-gray-700">Operating System</label>
									<select
										v-model="filters.os"
										class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
									>
										<option value="">All OS</option>
										<option v-for="os in uniqueOperatingSystems" :key="os" :value="os">
											{{ os }}
										</option>
									</select>
								</div>
								<div>
									<label class="mb-2 block text-sm font-medium text-gray-700">Search</label>
									<input
										v-model="filters.search"
										type="text"
										placeholder="Search hostname, IP, agent ID..."
										class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
									/>
								</div>
							</div>
							<div class="mt-4 flex justify-end">
								<button
									@click="clearFilters"
									class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
								>
									Clear Filters
								</button>
							</div>
						</div>
					</div>

					<!-- Agents Table -->
					<div class="overflow-hidden rounded-lg bg-white shadow-sm">
						<div class="border-b border-gray-200 px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900">Agents ({{ filteredAgents.length }})</h3>
						</div>
						<div v-if="filteredAgents.length === 0" class="p-6 text-center text-gray-500">
							No agents found matching your criteria.
						</div>
						<div v-else class="overflow-x-auto">
							<table class="min-w-full divide-y divide-gray-200">
								<thead class="bg-gray-50">
									<tr>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Agent
										</th>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Status
										</th>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Operating System
										</th>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Last Seen
										</th>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Version
										</th>
										<th
											scope="col"
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>
											Actions
										</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-gray-200 bg-white">
									<tr v-for="agent in paginatedAgents" :key="agent.id" class="hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="flex items-center">
												<div class="h-10 w-10 flex-shrink-0">
													<div
														class="flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium text-white"
														:class="{
															'bg-green-500': agent.wazuh_agent_status === 'active',
															'bg-red-500': agent.wazuh_agent_status === 'disconnected',
															'bg-yellow-500':
																agent.wazuh_agent_status === 'never_connected',
															'bg-gray-500': agent.wazuh_agent_status === 'pending'
														}"
													>
														{{ agent.hostname.charAt(0).toUpperCase() }}
													</div>
												</div>
												<div class="ml-4">
													<div class="text-sm font-medium text-gray-900">
														{{ agent.hostname }}
													</div>
													<div class="text-sm text-gray-500">{{ agent.ip_address }}</div>
													<div class="text-xs text-gray-400">ID: {{ agent.agent_id }}</div>
												</div>
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="flex items-center">
												<span
													class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
													:class="{
														'bg-green-100 text-green-800':
															agent.wazuh_agent_status === 'active',
														'bg-red-100 text-red-800':
															agent.wazuh_agent_status === 'disconnected',
														'bg-yellow-100 text-yellow-800':
															agent.wazuh_agent_status === 'never_connected',
														'bg-gray-100 text-gray-800':
															agent.wazuh_agent_status === 'pending'
													}"
												>
													{{ agent.wazuh_agent_status }}
												</span>
												<span
													v-if="agent.critical_asset"
													class="ml-2 inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800"
												>
													Critical
												</span>
												<span
													v-if="agent.quarantined"
													class="ml-2 inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
												>
													Quarantined
												</span>
											</div>
										</td>
										<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-900">
											{{ agent.os }}
										</td>
										<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											{{ formatTimeAgo(agent.wazuh_last_seen) }}
										</td>
										<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											<div>Wazuh: {{ agent.wazuh_agent_version }}</div>
											<div v-if="agent.velociraptor_agent_version" class="text-xs">
												VR: {{ agent.velociraptor_agent_version }}
											</div>
										</td>
										<td class="px-6 py-4 text-right text-sm font-medium whitespace-nowrap">
											<div class="flex space-x-2">
												<button
													v-if="!agent.critical_asset"
													@click="markAsCritical(agent)"
													class="text-xs text-orange-600 hover:text-orange-900"
													:disabled="updatingAgent === agent.agent_id"
												>
													Mark Critical
												</button>
												<button
													v-else
													@click="markAsNotCritical(agent)"
													class="text-xs text-gray-600 hover:text-gray-900"
													:disabled="updatingAgent === agent.agent_id"
												>
													Remove Critical
												</button>
												<button
													@click="viewAgentDetails(agent)"
													class="text-xs text-indigo-600 hover:text-indigo-900"
												>
													Details
												</button>
											</div>
										</td>
									</tr>
								</tbody>
							</table>
						</div>

						<!-- Pagination -->
						<div
							v-if="totalPages > 1"
							class="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6"
						>
							<div class="flex flex-1 justify-between sm:hidden">
								<button
									@click="previousPage"
									:disabled="currentPage <= 1"
									class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
								>
									Previous
								</button>
								<button
									@click="nextPage"
									:disabled="currentPage >= totalPages"
									class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
								>
									Next
								</button>
							</div>
							<div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
								<div>
									<p class="text-sm text-gray-700">
										Showing
										<span class="font-medium">{{ (currentPage - 1) * pageSize + 1 }}</span>
										to
										<span class="font-medium">
											{{ Math.min(currentPage * pageSize, filteredAgents.length) }}
										</span>
										of
										<span class="font-medium">{{ filteredAgents.length }}</span>
										results
									</p>
								</div>
								<div>
									<nav
										class="relative z-0 inline-flex -space-x-px rounded-md shadow-sm"
										aria-label="Pagination"
									>
										<button
											@click="previousPage"
											:disabled="currentPage <= 1"
											class="relative inline-flex items-center rounded-l-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Previous</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path
													fill-rule="evenodd"
													d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
										</button>
										<button
											v-for="page in visiblePages"
											:key="page"
											@click="typeof page === 'number' ? (currentPage = page) : null"
											:class="{
												'z-10 border-indigo-500 bg-indigo-50 text-indigo-600':
													page === currentPage,
												'border-gray-300 bg-white text-gray-500 hover:bg-gray-50':
													page !== currentPage
											}"
											class="relative inline-flex items-center border px-4 py-2 text-sm font-medium"
											:disabled="typeof page === 'string'"
										>
											{{ page }}
										</button>
										<button
											@click="nextPage"
											:disabled="currentPage >= totalPages"
											class="relative inline-flex items-center rounded-r-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Next</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path
													fill-rule="evenodd"
													d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
										</button>
									</nav>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</main>

		<!-- Agent Details Modal -->
		<div
			v-if="selectedAgent"
			class="bg-opacity-50 fixed inset-0 z-50 h-full w-full overflow-y-auto bg-gray-600"
			@click="closeAgentDetails"
		>
			<div
				class="relative top-20 mx-auto w-11/12 rounded-md border bg-white p-5 shadow-lg md:w-3/4 lg:w-1/2"
				@click.stop
			>
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-lg font-bold text-gray-900">Agent Details</h3>
					<button @click="closeAgentDetails" class="text-gray-400 hover:text-gray-600">
						<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>

				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<div>
						<label class="block text-sm font-medium text-gray-700">Hostname</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.hostname }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Agent ID</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.agent_id }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">IP Address</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.ip_address }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Operating System</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.os }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Wazuh Status</label>
						<span
							class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
							:class="{
								'bg-green-100 text-green-800': selectedAgent.wazuh_agent_status === 'active',
								'bg-red-100 text-red-800': selectedAgent.wazuh_agent_status === 'disconnected',
								'bg-yellow-100 text-yellow-800': selectedAgent.wazuh_agent_status === 'never_connected',
								'bg-gray-100 text-gray-800': selectedAgent.wazuh_agent_status === 'pending'
							}"
						>
							{{ selectedAgent.wazuh_agent_status }}
						</span>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Wazuh Version</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.wazuh_agent_version }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Last Seen (Wazuh)</label>
						<p class="mt-1 text-sm text-gray-900">{{ formatDateTime(selectedAgent.wazuh_last_seen) }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Velociraptor ID</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.velociraptor_id || "N/A" }}</p>
					</div>
					<div v-if="selectedAgent.velociraptor_agent_version">
						<label class="block text-sm font-medium text-gray-700">Velociraptor Version</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAgent.velociraptor_agent_version }}</p>
					</div>
					<div v-if="selectedAgent.velociraptor_last_seen">
						<label class="block text-sm font-medium text-gray-700">Last Seen (Velociraptor)</label>
						<p class="mt-1 text-sm text-gray-900">
							{{ formatDateTime(selectedAgent.velociraptor_last_seen) }}
						</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Critical Asset</label>
						<span
							class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
							:class="{
								'bg-orange-100 text-orange-800': selectedAgent.critical_asset,
								'bg-gray-100 text-gray-800': !selectedAgent.critical_asset
							}"
						>
							{{ selectedAgent.critical_asset ? "Yes" : "No" }}
						</span>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700">Quarantined</label>
						<span
							class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
							:class="{
								'bg-red-100 text-red-800': selectedAgent.quarantined,
								'bg-gray-100 text-gray-800': !selectedAgent.quarantined
							}"
						>
							{{ selectedAgent.quarantined ? "Yes" : "No" }}
						</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import AgentsAPI, { type Agent } from "@/api/agents"

const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const loading = ref(true)
const error = ref("")
const showLogo = ref(true)
const agents = ref<Agent[]>([])
const selectedAgent = ref<Agent | null>(null)
const updatingAgent = ref<string | null>(null)

// Filters
const filters = ref({
	status: "",
	critical: "",
	os: "",
	search: ""
})

// Pagination
const currentPage = ref(1)
const pageSize = ref(20)

const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})

const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

const uniqueOperatingSystems = computed(() => {
	const osSet = new Set(agents.value.map(agent => agent.os))
	return Array.from(osSet).sort()
})

const activeAgents = computed(() => {
	return agents.value.filter(agent => agent.wazuh_agent_status === "active").length
})

const criticalAgents = computed(() => {
	return agents.value.filter(agent => agent.critical_asset).length
})

const offlineAgents = computed(() => {
	return agents.value.filter(
		agent => agent.wazuh_agent_status === "disconnected" || agent.wazuh_agent_status === "never_connected"
	).length
})

const filteredAgents = computed(() => {
	let filtered = agents.value

	if (filters.value.status) {
		filtered = filtered.filter(agent => agent.wazuh_agent_status === filters.value.status)
	}

	if (filters.value.critical) {
		const isCritical = filters.value.critical === "true"
		filtered = filtered.filter(agent => agent.critical_asset === isCritical)
	}

	if (filters.value.os) {
		filtered = filtered.filter(agent => agent.os === filters.value.os)
	}

	if (filters.value.search) {
		const searchTerm = filters.value.search.toLowerCase()
		filtered = filtered.filter(
			agent =>
				agent.hostname.toLowerCase().includes(searchTerm) ||
				agent.ip_address.toLowerCase().includes(searchTerm) ||
				agent.agent_id.toLowerCase().includes(searchTerm)
		)
	}

	return filtered
})

const totalPages = computed(() => {
	return Math.ceil(filteredAgents.value.length / pageSize.value)
})

const paginatedAgents = computed(() => {
	const start = (currentPage.value - 1) * pageSize.value
	const end = start + pageSize.value
	return filteredAgents.value.slice(start, end)
})

const visiblePages = computed(() => {
	const total = totalPages.value
	const current = currentPage.value
	const delta = 2

	const range = []
	const rangeWithDots = []

	for (let i = Math.max(2, current - delta); i <= Math.min(total - 1, current + delta); i++) {
		range.push(i)
	}

	if (current - delta > 2) {
		rangeWithDots.push(1, "...")
	} else {
		rangeWithDots.push(1)
	}

	rangeWithDots.push(...range)

	if (current + delta < total - 1) {
		rangeWithDots.push("...", total)
	} else {
		rangeWithDots.push(total)
	}

	return rangeWithDots
		.filter((page, index, arr) => arr.indexOf(page) === index && page !== current - 1 && page !== current + 1)
		.slice(0, 7)
})

const formatTimeAgo = (dateString: string) => {
	if (!dateString) return "Never"

	try {
		const date = new Date(dateString)
		const now = new Date()
		const diffInMs = now.getTime() - date.getTime()
		const diffInMinutes = diffInMs / (1000 * 60)
		const diffInHours = diffInMs / (1000 * 60 * 60)
		const diffInDays = diffInMs / (1000 * 60 * 60 * 24)

		if (diffInMinutes < 60) {
			return `${Math.floor(diffInMinutes)} minutes ago`
		} else if (diffInHours < 24) {
			return `${Math.floor(diffInHours)} hours ago`
		} else if (diffInDays < 30) {
			return `${Math.floor(diffInDays)} days ago`
		} else {
			return date.toLocaleDateString()
		}
	} catch {
		return "Invalid date"
	}
}

const formatDateTime = (dateString: string) => {
	if (!dateString) return "N/A"

	try {
		const date = new Date(dateString)
		return date.toLocaleString()
	} catch {
		return "Invalid date"
	}
}

const loadAgents = async () => {
	loading.value = true
	error.value = ""

	try {
		const response = await AgentsAPI.getAgents()
		agents.value = response.agents || []
	} catch (err: any) {
		console.error("Failed to load agents:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to load agents"
		agents.value = []
	} finally {
		loading.value = false
	}
}

const markAsCritical = async (agent: Agent) => {
	updatingAgent.value = agent.agent_id
	try {
		await AgentsAPI.markAgentAsCritical(agent.agent_id)
		agent.critical_asset = true
	} catch (err: any) {
		console.error("Failed to mark agent as critical:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to update agent"
	} finally {
		updatingAgent.value = null
	}
}

const markAsNotCritical = async (agent: Agent) => {
	updatingAgent.value = agent.agent_id
	try {
		await AgentsAPI.markAgentAsNotCritical(agent.agent_id)
		agent.critical_asset = false
	} catch (err: any) {
		console.error("Failed to mark agent as not critical:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to update agent"
	} finally {
		updatingAgent.value = null
	}
}

const viewAgentDetails = (agent: Agent) => {
	selectedAgent.value = agent
}

const closeAgentDetails = () => {
	selectedAgent.value = null
}

const clearFilters = () => {
	filters.value = {
		status: "",
		critical: "",
		os: "",
		search: ""
	}
	currentPage.value = 1
}

const nextPage = () => {
	if (currentPage.value < totalPages.value) {
		currentPage.value++
	}
}

const previousPage = () => {
	if (currentPage.value > 1) {
		currentPage.value--
	}
}

const logout = () => {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

onMounted(() => {
	loadAgents()
})
</script>
