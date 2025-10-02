/**
 * plugins/vuetify.js
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

// Composables
import { createVuetify } from 'vuetify'

import { ru } from 'vuetify/locale'

// Импорт адаптера из @date-io/date-fns
import DateFnsAdapter from '@date-io/date-fns'
// Импорт русской локали для календаря из date-fns
import { ru as dateFnsLocale } from 'date-fns/locale'

import { VDateInput } from 'vuetify/labs/VDateInput'

// 1. ОПРЕДЕЛЯЕМ НАШУ НОВУЮ ТЕМУ
const gpbLight = {
  dark: false, // Мы будем работать в рамках одной светлой темы
  colors: {
    background: '#F5F5F5', // Светло-серый фон как на сайтах ГПБ
    surface: '#FFFFFF',    // Белый цвет для карточек, панелей
    primary: '#2455D8',    // Основной синий
    secondary: '#72AEFE',  // Второстепенный голубой
    
    // Цвета для тональностей
    positive: '#00875A',   // Насыщенный, но спокойный зеленый
    neutral: '#FFA500',    // Оранжевый для нейтральных
    negative: '#DE350B',   // Мягкий, но понятный красный (лучше розового для данных)
    
    // Стандартные цвета Vuetify, которые тоже стоит задать
    error: '#DE350B',
    info: '#72AEFE',
    success: '#00875A',
    warning: '#FFA500',
  }
}

const gpbDark = {
  dark: true,
  colors: {
    background: '#121212', // Глубокий темный фон
    surface: '#1E1E1E',    // Чуть более светлые карточки
    primary: '#72AEFE',    // Голубой становится основным для акцентов
    secondary: '#2455D8',
    // Цвета тональности можно оставить те же, они хорошо смотрятся на темном
    positive: '#00875A',
    neutral: '#FFA500',
    negative: '#DE350B',
    error: '#DE350B',
    info: '#72AEFE',
    success: '#00875A',
    warning: '#FFA500',
  }
}

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
// Экспортируем настроенный Vuetify
export default createVuetify({
  components: {
    VDateInput,
  },
  // Настройка общей локали
  locale: {
    locale: 'ru',
    messages: { ru },
  },
  // Настройка адаптера для работы с датами (v-date-picker)
  date: {
    // Используем правильный адаптер
    adapter: new DateFnsAdapter({
      // И передаем ему локаль
      formats: {
        // Вы можете переопределить форматы здесь, если нужно
      },
      locale: dateFnsLocale,
    }),
  },
  theme: {
    defaultTheme: 'gpbLight', // Устанавливаем нашу тему по умолчанию
    themes: {
      gpbLight,
      gpbDark,
    },
  },
  // 3. УСТАНАВЛИВАЕМ ШРИФТ ПО УМОЛЧАНИЮ ДЛЯ ВСЕХ КОМПОНЕНТОВ
  defaults: {
    global: {
      style: 'font-family: "Inter", sans-serif;',
    },
    VCard: {
      // elevation: 2, // Легкая тень для всех карточек
      elevation: 0,
      border: 'thin',
      class: 'rounded-lg' // Скругленные углы
    }
  }
})