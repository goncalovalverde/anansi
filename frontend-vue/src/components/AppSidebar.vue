<template>
  <nav class="app-sidebar" aria-label="Main navigation">
    <!-- Logo -->
    <div class="sidebar-logo">
      <svg class="logo-spider" xmlns="http://www.w3.org/2000/svg" viewBox="-2 0 36 36" fill="none" aria-hidden="true">
        <line x1="10" y1="14" x2="1"  y2="9"  stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="9"  y1="17" x2="0"  y2="17" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="10" y1="20" x2="1"  y2="25" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="11" y1="23" x2="4"  y2="30" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="22" y1="14" x2="31" y2="9"  stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="23" y1="17" x2="32" y2="17" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="22" y1="20" x2="31" y2="25" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="21" y1="23" x2="28" y2="30" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
        <polygon points="16,5 19,7 19,11 16,13 13,11 13,7" fill="#007B85"/>
        <polygon points="16,13 21,16 21,22 16,25 11,22 11,16" fill="#007B85"/>
        <polygon points="12,25 15,27 15,31 12,33 9,31 9,27"  fill="#F5A623"/>
        <polygon points="20,25 23,27 23,31 20,33 17,31 17,27" fill="#F5A623"/>
      </svg>
      <span class="sidebar-wordmark">ANANSI</span>
    </div>

    <hr class="sidebar-divider" />

    <!-- Top nav group -->
    <div class="sidebar-nav">
      <router-link to="/" class="sidebar-item" :class="{ active: route.path === '/' }" title="Dashboard" aria-label="Dashboard">
        <svg class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <rect x="14" y="14" width="7" height="7" rx="1"/>
        </svg>
        <span class="sidebar-item-label">Dashboard</span>
      </router-link>

      <router-link to="/flow" class="sidebar-item" :class="{ active: route.path === '/flow' }" title="Flow" aria-label="Flow">
        <svg class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M3 12 C6 6, 9 18, 12 12 C15 6, 18 18, 21 12"/>
        </svg>
        <span class="sidebar-item-label">Flow</span>
      </router-link>

      <button class="sidebar-item" aria-disabled="true" title="Trends — coming soon" aria-label="Trends (coming soon)">
        <svg class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <polyline points="3 17 8 12 13 16 21 7"/>
          <polyline points="15 7 21 7 21 13"/>
        </svg>
        <span class="sidebar-item-label">Trends</span>
      </button>
    </div>

    <!-- Bottom nav group -->
    <div class="sidebar-nav-bottom">
      <router-link to="/config" class="sidebar-item" :class="{ active: route.path === '/config' }" title="Configuration" aria-label="Configuration">
        <svg class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M19.07 19.07l-1.41-1.41M5.34 5.34L3.93 6.75M12 2v2M12 20v2M2 12h2M20 12h2"/>
        </svg>
        <span class="sidebar-item-label">Config</span>
      </router-link>

      <button class="sidebar-item" @click="configStore.toggleTheme()" :title="configStore.theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'" aria-label="Toggle dark mode">
        <svg v-if="configStore.theme === 'light'" class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <span class="sidebar-item-label">{{ configStore.theme === 'light' ? 'Dark' : 'Light' }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config.js'

const route = useRoute()
const configStore = useConfigStore()
</script>
