/**
 * main.js
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'

// Styles
import 'unfonts.css'

import Plotly from 'plotly.js-dist-min';
import locale from 'plotly.js-locales/ru'

Plotly.register(locale)
Plotly.setPlotConfig({locale: 'ru'})

const app = createApp(App)

registerPlugins(app)

app.mount('#app')