import { defineStore } from 'pinia'

export const useConfigStore = defineStore('config', {
  state: () => ({
    theme: localStorage.getItem('anansi_theme') || 'light',
  }),
  actions: {
    setTheme(t) {
      this.theme = t
      localStorage.setItem('anansi_theme', t)
      if (t === 'dark') {
        document.documentElement.classList.add('dark-mode')
      } else {
        document.documentElement.classList.remove('dark-mode')
      }
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },
    init() {
      this.setTheme(this.theme)
    },
  },
})
