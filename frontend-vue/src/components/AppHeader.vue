<template>
  <header class="app-header">
    <div class="container">
      <router-link to="/" class="app-logo" aria-label="Anansi — go to dashboard">
        <!-- Spider icon (inline SVG) -->
        <svg class="logo-spider" xmlns="http://www.w3.org/2000/svg" viewBox="-2 0 36 36" fill="none" aria-hidden="true">
          <!-- Legs -->
          <line x1="10" y1="14" x2="1"  y2="9"  stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="9"  y1="17" x2="0"  y2="17" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="10" y1="20" x2="1"  y2="25" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="11" y1="23" x2="4"  y2="30" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="22" y1="14" x2="31" y2="9"  stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="23" y1="17" x2="32" y2="17" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="22" y1="20" x2="31" y2="25" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="21" y1="23" x2="28" y2="30" stroke="#007B85" stroke-width="1.8" stroke-linecap="round"/>
          <!-- Head hex -->
          <polygon points="16,5 19,7 19,11 16,13 13,11 13,7" fill="#007B85"/>
          <!-- Body hex -->
          <polygon points="16,13 21,16 21,22 16,25 11,22 11,16" fill="#007B85"/>
          <!-- Gold belly -->
          <polygon points="12,25 15,27 15,31 12,33 9,31 9,27"  fill="#F5A623"/>
          <polygon points="20,25 23,27 23,31 20,33 17,31 17,27" fill="#F5A623"/>
        </svg>
        <div class="logo-text">
          <span class="logo-wordmark">ANANSI</span>
          <span class="logo-tagline">Unweaving Complexity</span>
        </div>
      </router-link>

      <nav class="nav-links">
        <router-link to="/" :class="{ active: route.path === '/' }">Dashboard</router-link>
        <router-link to="/config" :class="{ active: route.path === '/config' }">Configuration</router-link>
      </nav>

      <button class="theme-toggle" @click="configStore.toggleTheme()"
              title="Toggle light/dark mode" aria-label="Toggle theme">
        {{ configStore.theme === 'light' ? '🌙' : '☀️' }}
      </button>
    </div>
  </header>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config.js'
const route = useRoute()
const configStore = useConfigStore()
</script>

<style scoped>
.app-logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  flex-shrink: 0;
}
.logo-spider {
  height: 36px;
  width: auto;
  flex-shrink: 0;
}
.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.logo-wordmark {
  font-family: 'Raleway', 'Inter', sans-serif;
  font-weight: 800;
  font-size: 1.1rem;
  letter-spacing: 0.12em;
  color: var(--color-teal);
}
.logo-tagline {
  font-family: 'Inter', sans-serif;
  font-size: 0.6rem;
  font-weight: 400;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  text-transform: uppercase;
}
@media (max-width: 480px) {
  .logo-tagline { display: none; }
}
</style>
