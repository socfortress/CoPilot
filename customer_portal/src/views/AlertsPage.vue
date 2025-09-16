<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <button @click="goBack" class="mr-4 text-indigo-600 hover:text-indigo-500">
              ← Back
            </button>
            <h1 class="text-xl font-semibold text-gray-900">Security Alerts</h1>
          </div>
          <div class="flex items-center space-x-4">
            <button
              @click="refreshAlerts"
              :disabled="loading"
              class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <svg class="w-4 h-4 mr-2" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Total Alerts</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ stats.total }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Open</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ stats.open }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">In Progress</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ stats.in_progress }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Closed</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ stats.closed }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="bg-white shadow rounded-lg mb-6">
        <div class="px-4 py-5 sm:p-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label for="status-filter" class="block text-sm font-medium text-gray-700">Status</label>
              <select
                id="status-filter"
                v-model="filters.status"
                @change="applyFilters"
                class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <label for="source-filter" class="block text-sm font-medium text-gray-700">Source</label>
              <select
                id="source-filter"
                v-model="filters.source"
                @change="applyFilters"
                class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Sources</option>
                <option v-for="source in availableSources" :key="source" :value="source">{{ source }}</option>
              </select>
            </div>
            <div>
              <label for="asset-filter" class="block text-sm font-medium text-gray-700">Asset</label>
              <select
                id="asset-filter"
                v-model="filters.asset"
                @change="applyFilters"
                class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Assets</option>
                <option v-for="asset in availableAssets" :key="asset" :value="asset">{{ asset }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Alerts List -->
      <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <div v-if="loading" class="px-4 py-5 sm:p-6 text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p class="mt-2 text-sm text-gray-500">Loading alerts...</p>
        </div>

        <div v-else-if="error" class="px-4 py-5 sm:p-6 text-center">
          <div class="text-red-500 mb-2">
            <svg class="w-8 h-8 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
          </div>
          <p class="text-sm text-red-600">{{ error }}</p>
          <button
            @click="loadAlerts"
            class="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Try Again
          </button>
        </div>

        <ul v-else-if="alerts.length > 0" role="list" class="divide-y divide-gray-200">
          <li v-for="alert in alerts" :key="alert.id" class="px-4 py-4 sm:px-6 hover:bg-gray-50">
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-800': alert.status === 'OPEN',
                      'bg-yellow-100 text-yellow-800': alert.status === 'IN_PROGRESS',
                      'bg-green-100 text-green-800': alert.status === 'CLOSED'
                    }"
                  >
                    {{ alert.status.replace('_', ' ').toUpperCase() }}
                  </span>
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900">
                    {{ alert.alert_name }}
                  </div>
                  <div class="text-sm text-gray-500">
                    <span v-if="alert.assets.length > 0">
                      Asset: {{ alert.assets[0].asset_name }}
                    </span>
                    <span v-else-if="alert.asset_name">
                      Asset: {{ alert.asset_name }}
                    </span>
                    | Source: {{ alert.source }}
                  </div>
                  <div class="text-xs text-gray-400">
                    {{ formatDate(alert.alert_creation_time) }}
                  </div>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <select
                  :value="alert.status"
                  @change="updateAlertStatus(alert.id, ($event.target as HTMLSelectElement).value)"
                  class="text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  :disabled="updatingStatus === alert.id"
                >
                  <option value="OPEN">Open</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="CLOSED">Closed</option>
                </select>
                <button
                  @click="viewAlert(alert)"
                  class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  View Details
                </button>
              </div>
            </div>
            <div v-if="alert.alert_description" class="mt-2 text-sm text-gray-600">
              {{ alert.alert_description }}
            </div>
          </li>
        </ul>

        <div v-else class="px-4 py-5 sm:p-6 text-center">
          <svg class="w-12 h-12 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No alerts found</h3>
          <p class="mt-1 text-sm text-gray-500">No security alerts match your current filters.</p>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="alerts.length > 0" class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6 mt-6">
        <div class="flex-1 flex justify-between sm:hidden">
          <button
            @click="previousPage"
            :disabled="currentPage <= 1"
            class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            @click="nextPage"
            :disabled="currentPage >= totalPages"
            class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700">
              Showing <span class="font-medium">{{ (currentPage - 1) * pageSize + 1 }}</span>
              to <span class="font-medium">{{ Math.min(currentPage * pageSize, stats.total) }}</span>
              of <span class="font-medium">{{ stats.total }}</span> results
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
              <button
                @click="previousPage"
                :disabled="currentPage <= 1"
                class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                @click="nextPage"
                :disabled="currentPage >= totalPages"
                class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>

    <!-- Alert Details Modal -->
    <div v-if="selectedAlert" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" @click="closeModal">
      <div class="relative top-10 mx-auto p-5 border w-11/12 md:w-4/5 lg:w-3/4 shadow-lg rounded-md bg-white max-h-screen overflow-y-auto" @click.stop>
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium text-gray-900">Alert Details</h3>
          <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="space-y-6">
          <!-- Basic Alert Information -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Alert Name</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedAlert.alert_name }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Status</label>
              <span
                class="mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="{
                  'bg-red-100 text-red-800': selectedAlert.status === 'OPEN',
                  'bg-yellow-100 text-yellow-800': selectedAlert.status === 'IN_PROGRESS',
                  'bg-green-100 text-green-800': selectedAlert.status === 'CLOSED'
                }"
              >
                {{ selectedAlert.status.replace('_', ' ').toUpperCase() }}
              </span>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Source</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedAlert.source }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Customer</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedAlert.customer_code }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Created</label>
              <p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedAlert.alert_creation_time) }}</p>
            </div>
            <div v-if="selectedAlert.assigned_to">
              <label class="block text-sm font-medium text-gray-700">Assigned To</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedAlert.assigned_to }}</p>
            </div>
          </div>
          
          <div v-if="selectedAlert.alert_description">
            <label class="block text-sm font-medium text-gray-700">Description</label>
            <p class="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{{ selectedAlert.alert_description }}</p>
          </div>

          <!-- Assets Section -->
          <div v-if="selectedAlert.assets && selectedAlert.assets.length > 0">
            <label class="block text-sm font-medium text-gray-700 mb-2">Assets</label>
            <div class="bg-gray-50 rounded-lg p-4">
              <div v-for="asset in selectedAlert.assets" :key="asset.id" class="border-b border-gray-200 pb-3 mb-3 last:border-b-0 last:mb-0">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                  <div>
                    <span class="font-medium">Asset Name:</span> {{ asset.asset_name }}
                  </div>
                  <div>
                    <span class="font-medium">Agent ID:</span> {{ asset.agent_id }}
                  </div>
                  <div v-if="asset.velociraptor_id">
                    <span class="font-medium">Velociraptor ID:</span> {{ asset.velociraptor_id }}
                  </div>
                  <div>
                    <span class="font-medium">Index:</span> {{ asset.index_name }}
                  </div>
                  <div>
                    <span class="font-medium">Index ID:</span> {{ asset.index_id.substring(0, 20) }}...
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Fallback for legacy asset_name -->
          <div v-else-if="selectedAlert.asset_name">
            <label class="block text-sm font-medium text-gray-700">Asset</label>
            <p class="mt-1 text-sm text-gray-900">{{ selectedAlert.asset_name }}</p>
          </div>

          <!-- Tags Section -->
          <div v-if="selectedAlert.tags && selectedAlert.tags.length > 0">
            <label class="block text-sm font-medium text-gray-700">Tags</label>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="tag in selectedAlert.tags"
                :key="tag.id"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {{ tag.tag }}
              </span>
            </div>
          </div>

          <!-- Legacy Tags (for backward compatibility) -->
          <div v-else-if="selectedAlert.tag && selectedAlert.tag.length > 0">
            <label class="block text-sm font-medium text-gray-700">Tags</label>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="tag in selectedAlert.tag"
                :key="tag"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <!-- Linked Cases Section -->
          <div v-if="selectedAlert.linked_cases && selectedAlert.linked_cases.length > 0">
            <label class="block text-sm font-medium text-gray-700 mb-2">Linked Cases</label>
            <div class="bg-gray-50 rounded-lg p-4">
              <div v-for="linkedCase in selectedAlert.linked_cases" :key="linkedCase.id" class="border-b border-gray-200 pb-3 mb-3 last:border-b-0 last:mb-0">
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <h4 class="text-sm font-medium text-gray-900">{{ linkedCase.case_name }}</h4>
                    <p class="text-xs text-gray-600 mt-1">{{ linkedCase.case_description }}</p>
                    <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>Case #{{ linkedCase.id }}</span>
                      <span>Created: {{ formatDate(linkedCase.case_creation_time) }}</span>
                      <span v-if="linkedCase.assigned_to">Assigned to: {{ linkedCase.assigned_to }}</span>
                    </div>
                  </div>
                  <span
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-800': linkedCase.case_status === 'OPEN',
                      'bg-yellow-100 text-yellow-800': linkedCase.case_status === 'IN_PROGRESS',
                      'bg-green-100 text-green-800': linkedCase.case_status === 'CLOSED'
                    }"
                  >
                    {{ linkedCase.case_status.replace('_', ' ').toUpperCase() }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Legacy Case IDs (for backward compatibility) -->
          <div v-else-if="selectedAlert.case_ids && selectedAlert.case_ids.length > 0">
            <label class="block text-sm font-medium text-gray-700">Linked Cases</label>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="caseId in selectedAlert.case_ids"
                :key="caseId"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
              >
                Case #{{ caseId }}
              </span>
            </div>
          </div>

          <!-- IoCs Section -->
          <div v-if="selectedAlert.iocs && selectedAlert.iocs.length > 0">
            <label class="block text-sm font-medium text-gray-700 mb-2">Indicators of Compromise (IoCs)</label>
            <div class="bg-gray-50 rounded-lg p-4">
              <div v-for="ioc in selectedAlert.iocs" :key="ioc.id" class="border-b border-gray-200 pb-3 mb-3 last:border-b-0 last:mb-0">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                  <div>
                    <span class="font-medium">Value:</span> 
                    <code class="bg-gray-100 px-1 rounded text-xs">{{ ioc.ioc_value }}</code>
                  </div>
                  <div>
                    <span class="font-medium">Type:</span> {{ ioc.ioc_type }}
                  </div>
                  <div>
                    <span class="font-medium">Description:</span> {{ ioc.ioc_description }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Comments Section -->
          <div v-if="selectedAlert.comments && selectedAlert.comments.length > 0">
            <label class="block text-sm font-medium text-gray-700 mb-2">Comments ({{ selectedAlert.comments.length }})</label>
            <div class="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <div v-for="comment in selectedAlert.comments" :key="comment.id" class="border-b border-gray-200 pb-3 mb-3 last:border-b-0 last:mb-0">
                <div class="flex justify-between items-start mb-2">
                  <span class="text-sm font-medium text-gray-900">{{ comment.user_name }}</span>
                  <span class="text-xs text-gray-500">{{ formatDate(comment.created_at) }}</span>
                </div>
                <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ comment.comment }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AlertsAPI, { type Alert, type AlertsResponse } from '@/api/alerts'

const router = useRouter()

// Reactive data
const alerts = ref<Alert[]>([])
const stats = ref({
  total: 0,
  open: 0,
  in_progress: 0,
  closed: 0
})
const loading = ref(false)
const error = ref<string | null>(null)
const selectedAlert = ref<Alert | null>(null)
const updatingStatus = ref<number | null>(null)

// Pagination
const currentPage = ref(1)
const pageSize = ref(25)

// Filters
const filters = ref({
  status: '',
  source: '',
  asset: ''
})

// Computed properties
const totalPages = computed(() => Math.ceil(stats.value.total / pageSize.value))

const availableSources = computed(() => {
  const sources = new Set(alerts.value.map(alert => alert.source))
  return Array.from(sources).sort()
})

const availableAssets = computed(() => {
  const assets = new Set(alerts.value.map(alert => alert.asset_name))
  return Array.from(assets).sort()
})

// Methods
const goBack = () => {
  router.push('/')
}

const loadAlerts = async () => {
  loading.value = true
  error.value = null

  try {
    let response: AlertsResponse

    if (filters.value.status) {
      response = await AlertsAPI.getAlertsByStatus(filters.value.status as any)
    } else if (filters.value.source) {
      response = await AlertsAPI.getAlertsBySource(filters.value.source)
    } else if (filters.value.asset) {
      response = await AlertsAPI.getAlertsByAsset(filters.value.asset)
    } else {
      response = await AlertsAPI.getAlerts(currentPage.value, pageSize.value)
    }

    alerts.value = response.alerts
    stats.value = {
      total: response.total,
      open: response.open,
      in_progress: response.in_progress,
      closed: response.closed
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load alerts'
    console.error('Error loading alerts:', err)
  } finally {
    loading.value = false
  }
}

const refreshAlerts = () => {
  loadAlerts()
}

const applyFilters = () => {
  currentPage.value = 1
  loadAlerts()
}

const updateAlertStatus = async (alertId: number, newStatus: string) => {
  updatingStatus.value = alertId

  try {
    await AlertsAPI.updateAlertStatus(alertId, newStatus as any)

    // Update the local alert status
    const alert = alerts.value.find(a => a.id === alertId)
    if (alert) {
      alert.status = newStatus as any
    }

    // Refresh stats
    await loadAlerts()
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to update alert status'
    console.error('Error updating alert status:', err)
  } finally {
    updatingStatus.value = null
  }
}

const viewAlert = (alert: Alert) => {
  selectedAlert.value = alert
}

const closeModal = () => {
  selectedAlert.value = null
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    loadAlerts()
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    loadAlerts()
  }
}

// Lifecycle
onMounted(() => {
  loadAlerts()
})
</script>
