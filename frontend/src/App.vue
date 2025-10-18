<template>
  <v-app>
    
    <v-navigation-drawer
      v-model="drawerVisible"
      width="300"
      class="border-e rounded-te-lg rounded-be-lg overflow-hidden"
      app
    >
      <div class="d-flex flex-column fill-height">
        <div class="non-scrollable-header border-b">
          <div class="d-flex justify-space-between align-center pa-2">
            <span class="text-h6">Продукты и услуги</span>
            <v-tooltip text="Множественный выбор">
              <template v-slot:activator="{ props }">
                <v-btn 
                  v-bind="props"
                  @click="toggleMultiSelectMode"
                  :variant="isMultiSelectMode ? 'tonal' : 'text'" 
                  icon="mdi-check-all"
                ></v-btn>
              </template>
            </v-tooltip>
          </div>

          <div :style="{ visibility: isMultiSelectMode ? 'visible' : 'hidden' }">
            <v-list-item @click="selectAllProducts" class="select-all-item" density="compact">
              <template v-slot:prepend>
                <v-checkbox-btn 
                  density="compact"
                  :model-value="isAllProductsSelected"
                  :indeterminate="selectedProducts.length > 0 && !isAllProductsSelected"
                ></v-checkbox-btn>
              </template>
              <v-list-item-title><b>Выбрать все</b></v-list-item-title>
            </v-list-item>
          </div>
        </div>
        
        <!-- Прокручиваемый список -->
        <div class="list-wrapper">
          <v-list density="compact">
            <v-list-item 
              v-for="product in products" 
              :key="product" 
              :value="product"
              @click="handleProductClick(product)"
              :active="selectedProducts.includes(product)"
            >
              <template v-if="isMultiSelectMode" v-slot:prepend>
                  <v-checkbox-btn 
                    density="compact"
                    :model-value="selectedProducts.includes(product)"
                    @click.stop="handleProductClick(product)"
                  ></v-checkbox-btn>
              </template>

              <v-list-item-title class="product-title" :title="product">{{ product }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>
      </div>
    </v-navigation-drawer>
        
    <v-main>
      <v-container fluid class="pa-5"> 
        <v-row>
          <v-col cols="12" class="pa-2">
            <v-card>
              <v-row align="center" class="ma-0">
                <v-col cols="auto">
                  <v-btn
                    variant="icon"
                    icon="mdi-menu"
                    @click="drawerVisible = !drawerVisible"
                  ></v-btn>
                </v-col>

                <v-col>
                  <span class="text-h6">{{ pageTitle }}</span>
                </v-col>

                <v-col cols="auto" class="d-flex align-center">
                  <!-- Фильтр по источникам -->
                  <v-btn-toggle
                    v-model="selectedSources"
                    multiple
                    mandatory
                    density="compact"
                    variant="outlined"
                    divided
                    class="mr-2"
                  >
                    <v-btn v-for="source in availableSources" :key="source" :value="source">
                      {{ source }}
                    </v-btn>
                  </v-btn-toggle>
                  <v-date-input
                    v-model="dateRange"
                    multiple="range"
                    variant="outlined"
                    density="compact"
                    hide-details
                    label="Период"
                    class="date-input-fix mr-2"
                    prepend-icon=""
                    @update:modelValue="onDateRangeChange"
                  ></v-date-input>

                  <v-btn-toggle
                    v-model="granularity"
                    mandatory
                    density="compact"
                    variant="outlined"
                    divided
                    label="Гранулярность"
                    class="mr-2"
                    ><v-btn value="month" :disabled="isMonthDisabled">Месяц</v-btn>
                    <v-btn value="week" :disabled="isWeekDisabled">Неделя</v-btn>
                    <v-btn value="day">День</v-btn>
                  </v-btn-toggle>

                  <v-btn
                    @click="toggleTheme"
                    :icon="vuetifyTheme.global.name.value === 'gpbDark' ? 'mdi-weather-sunny' : 'mdi-weather-night'"
                    variant="icon"
                  ></v-btn>
                </v-col>
              </v-row>
            </v-card>
          </v-col>

          <v-col cols="12" lg="6" class="pa-2">
            <v-card title="Распределение по тональности, отзывы">
              <v-card-text>
                <v-row align="center" no-gutters>
                  <v-col v-for="sentiment in ['positive', 'neutral', 'negative']" :key="sentiment" class="d-flex flex-column align-center">
                    <div class="d-flex align-baseline">
                      <span :class="`text-h4 text-${sentiment}`">{{ kpiAbs[sentiment].value }}</span>
                    </div>
                    <!-- Логика отображения тренда -->
                    <v-chip :color="isLoading ? 'grey' : getTrendColor(sentiment, kpiAbs[sentiment].trend)" size="small" class="mt-2" style="min-width: 100px; justify-content: center;">
                      <template v-if="isLoading">
                        <v-progress-circular indeterminate size="12" width="2" class="mr-1"></v-progress-circular>
                        <span>обновление...</span>
                      </template>
                      <template v-else>
                        <v-icon v-if="kpiAbs[sentiment].trend !== 0" size="small" start :icon="kpiAbs[sentiment].trend > 0 ? 'mdi-arrow-up' : 'mdi-arrow-down'"></v-icon>
                        {{ kpiAbs[sentiment].trend > 0 ? '+' : '' }}{{ kpiAbs[sentiment].trend }} {{ trendPeriodText }}
                      </template>
                    </v-chip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" lg="6" class="pa-2">
            <v-card title="Распределение по тональности, %">
              <v-card-text>
                <v-row align="center" no-gutters>
                  <v-col v-for="sentiment in ['positive', 'neutral', 'negative']" :key="sentiment" class="d-flex flex-column align-center">
                    <div class="d-flex align-baseline">
                      <span :class="`text-h4 text-${sentiment}`">{{ kpiPerc[sentiment].value }}%</span>
                    </div>
                    <v-chip :color="isLoading ? 'grey' : getTrendColor(sentiment, kpiPerc[sentiment].trend)" size="small" class="mt-2" style="min-width: 100px; justify-content: center;">
                      <template v-if="isLoading">
                        <v-progress-circular indeterminate size="12" width="2" class="mr-1"></v-progress-circular>
                        <span>обновление...</span>
                      </template>
                      <template v-else>
                        <v-icon v-if="kpiPerc[sentiment].trend !== 0" size="small" start :icon="kpiPerc[sentiment].trend > 0 ? 'mdi-arrow-up' : 'mdi-arrow-down'"></v-icon>
                        {{ kpiPerc[sentiment].trend > 0 ? '+' : '' }}{{ kpiPerc[sentiment].trend }} п.п. {{ trendPeriodText }}
                      </template>
                    </v-chip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" lg="6" class="pa-2">
            <v-card title="Динамика по тональностям, отзывы">
              <div ref="dynamicsCountChartDiv" class="chart-container"></div>
            </v-card>
          </v-col>
          
          <v-col cols="12" lg="6" class="pa-2">
            <v-card title="Динамика по тональностям, %">
              <div ref="dynamicsShareChartDiv" class="chart-container"></div>
            </v-card>
          </v-col>       
        </v-row>
      </v-container>
          
      <v-footer app class="d-flex justify-center text-caption">
        <span class="mr-1">Источники отзывов:</span>
        <a href="https://banki.ru" target="_blank" class="text-decoration-none text-primary">banki.ru</a>
        <span class="mr-1">,</span>
        <a href="https://sravni.ru" target="_blank" class="text-decoration-none text-primary">sravni.ru</a>
      </v-footer>
    </v-main>
  </v-app>
</template>


<script setup>

import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue';
import { useTheme } from 'vuetify';
import Plotly from 'plotly.js-dist-min';
import axios from 'axios';


const isLoading = ref(false);
const drawerVisible = ref(true);

const vuetifyTheme = useTheme();
const toggleTheme = () => {
  vuetifyTheme.global.name.value = vuetifyTheme.global.current.value.dark ? 'gpbLight' : 'gpbDark';
};

// --- API-клиент ---
const apiClient = axios.create({
  baseURL: `${window.location.protocol}//${window.location.hostname}:8000/api`,// Адрес Docker-бэкенда
});

// --- Реактивные переменные ---
const isMultiSelectMode = ref(false);
const products = ref([]);
const selectedProducts = ref([]);
const availableSources = ref([]);
const selectedSources = ref([]);

const dateRange = ref([new Date('2024-01-01'), new Date('2025-05-31')]);
const granularity = ref('month');

// --- Переменные для данных от API ---
const kpiAbs = ref({
  positive: { value: 0, trend: 0 },
  neutral: { value: 0, trend: 0 },
  negative: { value: 0, trend: 0 },
});
const kpiPerc = ref({
  positive: { value: 0, trend: 0 },
  neutral: { value: 0, trend: 0 },
  negative: { value: 0, trend: 0 },
});

// --- Refs для графиков ---
const dynamicsCountChartDiv = ref(null);
const dynamicsShareChartDiv = ref(null);

// --- Computed свойство для отслеживания состояния "Выбрать все" ---
const isAllProductsSelected = computed(() => {
return products.value.length > 0 && selectedProducts.value.length === products.value.length;
});

// --- Computed свойства ---
// Динамический заголовок страницы
const pageTitle = computed(() => {
  if (selectedProducts.value.length === products.value.length) {
    return 'Все продукты выбраны';
  }
  if (selectedProducts.value.length === 1) {
    return selectedProducts.value[0];
  }
  if (selectedProducts.value.length > 1) {
    return `Выбрано продуктов: ${selectedProducts.value.length}`;
  }
  return 'Аналитика клиентских настроений';
});

// Computed для цветов
const chartThemeColors = computed(() => {
  return vuetifyTheme.global.current.value.dark
    ? { font: '#FFFFFF', grid: '#424242' }
    : { font: '#333333', grid: '#E0E0E0' };
});

const trendPeriodText = computed(() => {
  switch (granularity.value) {
    case 'day': return 'за день';
    case 'week': return 'за неделю';
    case 'month': return 'за месяц';
    default: return '';
  }
});

// Computed свойство для вычисления разницы в днях
const dateRangeDaysDiff = computed(() => {
  if (Array.isArray(dateRange.value) && dateRange.value.length > 1 && dateRange.value[0] && dateRange.value[1]) {
    const start = new Date(dateRange.value[0]);
    const end = new Date(dateRange.value[dateRange.value.length - 1]);
    const diffTime = Math.abs(end - start);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }
  return 0;
});

// Computed свойства для блокировки кнопок
const isWeekDisabled = computed(() => dateRangeDaysDiff.value < 7);
const isMonthDisabled = computed(() => dateRangeDaysDiff.value < 31);

// Функция для определения цвета тренда
const getTrendColor = (sentiment, trend) => {
  if (trend === 0 || sentiment === 'neutral') {
    return 'grey';
  }
  if (sentiment === 'positive') {
    return trend > 0 ? 'green' : 'red';
  }
  if (sentiment === 'negative') {
    return trend > 0 ? 'red' : 'green';
  }
  return 'grey';
};

// Переключатель режима
const toggleMultiSelectMode = () => {
  isMultiSelectMode.value = !isMultiSelectMode.value;
  // Если вышли из мульти-режима и что-то выбрано, оставляем только первый элемент
  if (!isMultiSelectMode.value && selectedProducts.value.length > 1) {
    selectedProducts.value = [selectedProducts.value[0]];
  }
};

// Универсальный обработчик клика по продукту
const handleProductClick = (product) => {
  if (isMultiSelectMode.value) {
    // В режиме мульти-выбора: добавляем или убираем продукт из массива
    const index = selectedProducts.value.indexOf(product);
    if (index > -1) {
      // Запрещаем убирать последний выбранный элемент
      if (selectedProducts.value.length > 1) {
        selectedProducts.value.splice(index, 1);
      }
    } else {
      selectedProducts.value.push(product);
    }
  } else {
    // В режиме одиночного выбора: просто заменяем массив
    selectedProducts.value = [product];
  }
};

const selectAllProducts = () => {
  if (isAllProductsSelected.value) {
    // Если все выбраны, снимаем выбор, оставляя только первый элемент
    if (products.value.length > 0) {
      selectedProducts.value = [products.value[0]];
    } else {
      selectedProducts.value = [];
    }
  } else {
    // Если выбраны не все, выбираем все
    selectedProducts.value = [...products.value];
  }
};

// Функция для корректного форматирования даты
const formatDate = (date) => {
  if (!date) return null;
  const d = new Date(date);

  if (isNaN(d.getTime())) {
    console.error('Получена невалидная дата:', date);
    return null;
  }

  const year = d.getFullYear();
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const day = d.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const redrawCharts = () => {
  if (dynamicsCountChartDiv.value?.layout) Plotly.Plots.resize(dynamicsCountChartDiv.value);
  if (dynamicsShareChartDiv.value?.layout) Plotly.Plots.resize(dynamicsShareChartDiv.value);
};

const updateChartsTheme = () => {
  const plotlyLayoutUpdate = {
    'font.color': chartThemeColors.value.font,
    'xaxis.gridcolor': chartThemeColors.value.grid,
    'yaxis.gridcolor': chartThemeColors.value.grid,
  };
  if (dynamicsCountChartDiv.value?.layout) {
    Plotly.relayout(dynamicsCountChartDiv.value, plotlyLayoutUpdate);
  }
  if (dynamicsShareChartDiv.value?.layout) {
    Plotly.relayout(dynamicsShareChartDiv.value, plotlyLayoutUpdate);
  }
};

// --- ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ С БЭКЕНДА ---
const fetchData = async (overrideStartDate = null, overrideEndDate = null) => {
  const sDate = overrideStartDate || (dateRange.value ? dateRange.value[0] : null);
  const eDate = overrideEndDate || (dateRange.value ? dateRange.value[dateRange.value.length - 1] : null);

  if (!sDate || !eDate || selectedProducts.value.length === 0 || selectedSources.value.length === 0) {
    console.log("FetchData: Недостаточно данных для запроса (даты, продукты или источники не выбраны).");
    return;
  }

  isLoading.value = true;

  try {
    const params = {
      products: selectedProducts.value.join(','),
      sources: selectedSources.value.join(','),
      start_date: formatDate(sDate),
      end_date: formatDate(eDate),
      granularity: granularity.value,
    };

    const [
      kpiRes,
      dynamicsCountRes,
      dynamicsShareRes,
    ] = await Promise.all([
      apiClient.get('/kpi_summary', { params }),
      apiClient.get('/dynamics_stacked_bar', { params }),
      apiClient.get('/dynamics', { params }),
    ]);

    kpiAbs.value = kpiRes.data.kpiAbs;
    kpiPerc.value = kpiRes.data.kpiPerc;

    const commonLayout = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: chartThemeColors.value.font },
      // Добавляем traceorder, чтобы зафиксировать порядок в легенде
      legend: { 
        orientation: 'h', 
        yanchor: 'bottom', 
        y: 1.02, 
        xanchor: 'left', 
        x: 0,
        traceorder: 'reversed' 
      },
      margin: { t: 40, b: 30, l: 40, r: 20 },
      // Добавляем automargin для автоматического подбора отступов
      xaxis: { 
        gridcolor: chartThemeColors.value.grid,
        automargin: true
      },
      yaxis: { 
        gridcolor: chartThemeColors.value.grid,
        automargin: true
      }
    };

    const plotConfig = { responsive: true, displaylogo: false };
        
    // --- График Динамики Количества (Stacked Bar) ---
    if (dynamicsCountChartDiv.value) {
      // Запоминаем текущий зум, если он был установлен пользователем
      const existingLayout = dynamicsCountChartDiv.value.layout;
      const userZoom = {};
      if (existingLayout && existingLayout.xaxis.autorange === false) {
        userZoom.xaxis = { range: existingLayout.xaxis.range };
      }
      if (existingLayout && existingLayout.yaxis.autorange === false) {
        userZoom.yaxis = { range: existingLayout.yaxis.range };
      }

      const countLayout = { 
        ...commonLayout,
        barmode: 'stack',
        yaxis: { ...commonLayout.yaxis, title: 'Количество отзывов', ...userZoom.yaxis },
        xaxis: { ...commonLayout.xaxis, ...userZoom.xaxis }
      };
      Plotly.react(dynamicsCountChartDiv.value, dynamicsCountRes.data.data, countLayout, plotConfig);
    }

    // --- График Динамики Долей (Stacked Area) ---
    if (dynamicsShareChartDiv.value) {
      // Делаем то же самое для второго графика
      const existingLayout = dynamicsShareChartDiv.value.layout;
      const userZoom = {};
      if (existingLayout && existingLayout.xaxis.autorange === false) {
        userZoom.xaxis = { range: existingLayout.xaxis.range };
      }
      if (existingLayout && existingLayout.yaxis.autorange === false) {
        userZoom.yaxis = { range: existingLayout.yaxis.range };
      }

      const shareLayout = { 
        ...commonLayout, 
        yaxis: { ...commonLayout.yaxis, title: 'Доля, %', ...userZoom.yaxis },
        xaxis: { ...commonLayout.xaxis, ...userZoom.xaxis }
        };
      Plotly.react(dynamicsShareChartDiv.value, dynamicsShareRes.data.data, shareLayout, plotConfig);
    }
  } catch (error) {
    console.error("Ошибка при загрузке данных с бэкенда:", error);
  } finally {
    isLoading.value = false; // <-- Снимаем флаг загрузки в любом случае
  }
};

const onDateRangeChange = (newRange) => {
  // Проверяем, что диапазон полностью выбран
  if (Array.isArray(newRange) && newRange.length > 1 && newRange[0] && newRange[1]) {
    // Сортируем даты, чтобы гарантировать правильный порядок
    const dates = [...newRange].sort((a, b) => new Date(a) - new Date(b));
    const startDate = dates[0];
    const endDate = dates[dates.length - 1]; // Берем последний элемент на случай, если массив будет > 2
    fetchData(startDate, endDate);
  }
};

const selectSingleProduct = (product) => {
  selectedProducts.value = [product];
};

watch(selectedSources, (newValue, oldValue) => {
  // Правило: не даем пользователю убрать выбор со всех источников
  if (newValue.length === 0) {
    selectedSources.value = oldValue; // Возвращаем предыдущее значение
    return;
  }
  fetchData();
}, { deep: true });

watch(selectedProducts, (newValue, oldValue) => {
  if (newValue.length === 0 && oldValue && oldValue.length > 0) {
    selectedProducts.value = [...oldValue];
    return;
  }
  
  fetchData();
}, { deep: true });


watch(granularity, () => {
  fetchData(); 
});

// Watch для автоматической смены гранулярности, если текущая стала недоступна
watch(dateRangeDaysDiff, (newDiff) => {
  if (granularity.value === 'month' && newDiff < 31) {
    granularity.value = 'day';
  }
  if (granularity.value === 'week' && newDiff < 7) {
    granularity.value = 'day';
  }
});

watch(() => vuetifyTheme.global.name.value, updateChartsTheme);

let chartResizeObserver = null;

onMounted(async () => {
  try {
    const [productsResponse, sourcesResponse] = await Promise.all([
      apiClient.get('/products_list'),
      apiClient.get('/sources_list')
    ]);

    products.value = productsResponse.data;
    availableSources.value = sourcesResponse.data;

    // --- Устанавливаем состояние по умолчанию ---
    // 1. Выбираем первый продукт из списка
    if (products.value.length > 0) {
      selectedProducts.value = [products.value[0]];
    }
    // 2. Выбираем все источники
    if (availableSources.value.length > 0) {
      selectedSources.value = [...availableSources.value];
    }

    await fetchData();
  } catch (error) { console.error("Не удалось загрузить список продуктов:", error); }

  // Инициализируем ResizeObserver
  // Он вызывает redrawCharts мгновенно при любом изменении размера контейнеров
  chartResizeObserver = new ResizeObserver(() => {
    redrawCharts();
  });

  // Начинаем следить за обоими контейнерами для графиков
  if (dynamicsCountChartDiv.value) {
    chartResizeObserver.observe(dynamicsCountChartDiv.value);
  }
  if (dynamicsShareChartDiv.value) {
    chartResizeObserver.observe(dynamicsShareChartDiv.value);
  }
});

// Отключаем слежение, когда компонент уничтожается, чтобы избежать утечек памяти
onBeforeUnmount(() => {
  if (chartResizeObserver) {
    chartResizeObserver.disconnect();
  }
});
</script>


<style scoped>
.non-scrollable-header {
  flex-shrink: 0;
}

.list-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.select-all-item .v-list-item__prepend > .v-list-item-action {
  margin-inline-start: -8px !important;
  margin-inline-end: 24px !important;
}

.v-list-item-title.product-title {
  white-space: normal;
  word-break: break-word;
  line-height: 1.25rem;
  font-size: 0.875rem;
  transition: opacity 0.2s ease-in-out;
}

.v-list-item {
  height: auto !important;
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.date-input-fix {
  min-width: 210px;
  max-width: 210px;
  margin-top: 0;
}

:deep(.v-list-item--density-compact .v-list-item__prepend) {
  /* Позволяем содержимому (чекбоксу) определять ширину */
  min-width: auto;
  /* Уменьшаем стандартный большой отступ справа от чекбокса */
  margin-inline-end: 12px;
}
</style>