<template>
  <nav class="app-sidebar" aria-label="Main navigation">
    <!-- Logo -->
    <div class="sidebar-logo">
      <img class="logo-image" src="/logo.png" alt="Anansi logo" />
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

      <router-link to="/trends" class="sidebar-item" :class="{ active: route.path === '/trends' }" title="Trends" aria-label="Trends">
        <svg class="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <polyline points="3 17 8 12 13 16 21 7"/>
          <polyline points="15 7 21 7 21 13"/>
        </svg>
        <span class="sidebar-item-label">Trends</span>
      </router-link>
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
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
