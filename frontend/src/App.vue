<template>
  <!-- <v-app :theme="theme"> -->
  <v-app>
    
    <v-navigation-drawer
      v-model="drawerVisible"
      width="300"
    >
      <div class="d-flex flex-column fill-height">
        <div class="non-scrollable-header">
          <v-list-subheader class="font-weight-bold text-uppercase pa-4">Продукты и услуги</v-list-subheader>
        </div>
        
        <div class="list-wrapper">
          <v-list density="compact" select-strategy="multiple" v-model:selected="selectedProducts">
            <v-list-item @click="selectAllProducts" class="select-all-item">
              <template v-slot:prepend>
                <v-list-item-action start>
                  <v-checkbox-btn 
                    :model-value="isAllProductsSelected"
                    :indeterminate="selectedProducts.length > 0 && !isAllProductsSelected"
                  ></v-checkbox-btn>
                </v-list-item-action>
              </template>
              <v-list-item-title>Выбрать все</v-list-item-title>
            </v-list-item>
            <v-divider></v-divider>

            <v-hover v-for="product in products" :key="product" v-slot="{ isHovering, props }">
              <v-list-item :value="product" v-bind="props">
                <!-- Чекбокс для множественного выбора -->
                <template v-slot:prepend="{ isActive }">
                  <v-list-item-action start>
                    <v-checkbox-btn :model-value="isActive"></v-checkbox-btn>
                  </v-list-item-action>
                </template>

                <v-list-item-title class="product-title" :title="product">{{ product }}</v-list-item-title>
                
                <!-- Кнопка для одиночного выбора, которая появляется по наведению -->
                <template v-slot:append>
                  <v-btn
                    v-if="isHovering"
                    size="x-small"
                    variant="text"
                    icon="mdi-radiobox-marked"
                    title="Выбрать только этот продукт"
                    @click.stop="selectSingleProduct(product)"
                  ></v-btn>
                </template>
              </v-list-item>
            </v-hover>
          </v-list>
        </div>
      </div>
    </v-navigation-drawer>
    
    <v-main>
      <v-container fluid class="pa-4"> 
        <v-card class="mb-4">
          <v-row align="center" class="pa-2 ma-0">
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

            <v-col cols="auto">
              <v-row align="center" no-gutters>
                <v-date-input
                  v-model="dateRange"
                  multiple="range"
                  variant="outlined"
                  density="compact"
                  hide-details
                  label="Период"
                  class="date-input-fix mr-2"
                  @update:modelValue="onDateRangeChange"
                ></v-date-input>

                <v-btn-toggle
                  v-model="granularity"
                  mandatory
                  density="compact"
                  variant="outlined"
                  divided
                  label="Гранулярность"
                  ><v-btn value="day">День</v-btn>
                  <v-btn value="week" :disabled="isWeekDisabled">Неделя</v-btn>
                  <v-btn value="month" :disabled="isMonthDisabled">Месяц</v-btn>
                </v-btn-toggle>

                <v-btn
                  @click="toggleTheme"
                  :icon="vuetifyTheme.global.name.value === 'gpbDark' ? 'mdi-weather-sunny' : 'mdi-weather-night'"
                  variant="text"
                  class="ml-2"
                ></v-btn>
              </v-row>
            </v-col>
          </v-row>
        </v-card>
        
        <v-row density="compact">
          <v-col cols="12" lg="6">
            <v-card title="Распределение по тональности (абс.)">
              <v-card-text>
                <v-row align="center" no-gutters>
                  <v-col v-for="sentiment in ['positive', 'neutral', 'negative']" :key="sentiment" class="d-flex flex-column align-center">
                    <div class="d-flex align-baseline">
                      <span :class="`text-h4 text-${sentiment}`">{{ kpiAbs[sentiment].value }}</span>
                      <span class="ml-1 text-body-2 text-grey">шт.</span>
                    </div>
                    <!-- Логика отображения тренда -->
                    <v-chip :color="getTrendColor(sentiment, kpiAbs[sentiment].trend)" size="small" class="mt-2">
                      <v-icon v-if="kpiAbs[sentiment].trend !== 0" size="small" start :icon="kpiAbs[sentiment].trend > 0 ? 'mdi-arrow-up' : 'mdi-arrow-down'"></v-icon>
                        {{ kpiAbs[sentiment].trend > 0 ? '+' : '' }}{{ kpiAbs[sentiment].trend }} шт. {{ trendPeriodText }}
                    </v-chip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" lg="6">
            <v-card title="Распределение по тональности (%)">
              <v-card-text>
                <v-row align="center" no-gutters>
                  <v-col v-for="sentiment in ['positive', 'neutral', 'negative']" :key="sentiment" class="d-flex flex-column align-center">
                    <div class="d-flex align-baseline">
                      <span :class="`text-h4 text-${sentiment}`">{{ kpiPerc[sentiment].value }}</span>
                      <span class="ml-1 text-body-2 text-grey">%</span>
                    </div>
                    <v-chip :color="getTrendColor(sentiment, kpiPerc[sentiment].trend)" size="small" class="mt-2">
                      <v-icon v-if="kpiPerc[sentiment].trend !== 0" size="small" start :icon="kpiPerc[sentiment].trend > 0 ? 'mdi-arrow-up' : 'mdi-arrow-down'"></v-icon>
                        {{ kpiPerc[sentiment].trend > 0 ? '+' : '' }}{{ kpiPerc[sentiment].trend }} п.п. {{ trendPeriodText }}
                    </v-chip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row density="compact" class="mt-2">
          <v-col cols="12" lg="6">
            <v-card title="Динамика количества отзывов">
              <div ref="dynamicsCountChartDiv" class="chart-container"></div>
            </v-card>
          </v-col>
          
          <v-col cols="12" lg="6">
            <v-card title="Динамика долей тональностей (%)">
              <div ref="dynamicsShareChartDiv" class="chart-container"></div>
            </v-card>
          </v-col>
        </v-row>

        <v-row density="compact" class="mt-2">
          <v-col cols="12">
            <v-card title="Ключевые аспекты">
              <v-data-table
                :items="keyAspects"
                :headers="[{ title: 'Аспект', key: 'aspect' },{ title: 'Тональность', key: 'sentiment' },{ title: 'Кол-во отзывов', key: 'count', align: 'end' },{ title: 'Тренд за период', key: 'trend', align: 'end' }]"
                density="compact"
              >
                <template v-slot:item.sentiment="{ item }"><v-chip :color="item.sentiment === 'positive' ? 'green' : item.sentiment === 'negative' ? 'red' : 'orange'" variant="tonal" size="small">{{ item.sentiment }}</v-chip></template>
                <template v-slot:item.trend="{ item }"><v-chip :color="item.trend > 0 ? 'green' : 'red'"><v-icon start :icon="item.trend > 0 ? 'mdi-arrow-up' : 'mdi-arrow-down'"></v-icon>{{ Math.abs(item.trend) }}%</v-chip></template>
              </v-data-table>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>


<script setup>

import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue';
import { useTheme } from 'vuetify';
import Plotly from 'plotly.js-dist-min';
import axios from 'axios';


const drawerVisible = ref(true);
// const theme = ref('light');
// const toggleTheme = () => {
//   theme.value = theme.value === 'light' ? 'dark' : 'light';
// };
const vuetifyTheme = useTheme();
const toggleTheme = () => {
  vuetifyTheme.global.name.value = vuetifyTheme.global.current.value.dark ? 'gpbLight' : 'gpbDark';
};

// --- API-клиент ---
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api', // Адрес Docker-бэкенда
});

// --- Реактивные переменные ---
const products = ref([]);
const selectedProducts = ref([]);

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

const keyAspects = ref([]);
const reviews = ref([]);

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
    return 'Аналитика по всем продуктам';
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

// Логика для выбора продуктов
const selectAllProducts = () => {
  if (!isAllProductsSelected.value) {
    selectedProducts.value = [...products.value];
  } else {
    selectedProducts.value = products.value.length > 0 ? [products.value[0]] : [];
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

  if (!sDate || !eDate || selectedProducts.value.length === 0) {
    console.log("FetchData: Недостаточно данных для запроса (даты или продукты не выбраны).");
    return;
  }

  try {
    const params = {
      products: selectedProducts.value.join(','),
      start_date: formatDate(sDate),
      end_date: formatDate(eDate),
      granularity: granularity.value,
    };

    const [
      kpiRes,
      keyAspectsRes,
      dynamicsCountRes,
      dynamicsShareRes,
      reviewsRes
    ] = await Promise.all([
      apiClient.get('/kpi_summary', { params }),
      apiClient.get('/key_aspects', { params }),
      apiClient.get('/dynamics_stacked_bar', { params }),
      apiClient.get('/dynamics', { params }),
      apiClient.get('/reviews', { params }),
    ]);

  kpiAbs.value = kpiRes.data.kpiAbs;
  kpiPerc.value = kpiRes.data.kpiPerc;
  keyAspects.value = keyAspectsRes.data;
  reviews.value = reviewsRes.data;

  const commonLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: chartThemeColors.value.font },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    margin: { t: 40, b: 30, l: 40, r: 20 },
    xaxis: { gridcolor: chartThemeColors.value.grid },
    yaxis: { gridcolor: chartThemeColors.value.grid }
  };

  const plotConfig = { responsive: true, displaylogo: false };
      if (dynamicsCountChartDiv.value) {
        const layout = { ...dynamicsCountRes.data.layout, ...commonLayout };
        Plotly.react(dynamicsCountChartDiv.value, dynamicsCountRes.data.data, layout, plotConfig);
      }
      if (dynamicsShareChartDiv.value) {
        const layout = { ...dynamicsShareRes.data.layout, ...commonLayout };
        Plotly.react(dynamicsShareChartDiv.value, dynamicsShareRes.data.data, layout, plotConfig);
      }
    } catch (error) {
      console.error("Ошибка при загрузке данных с бэкенда:", error);
    }
};

const onDateRangeChange = (newRange) => {
  if (Array.isArray(newRange) && newRange.length > 1) {
    const startDate = newRange[0];
    const endDate = newRange[newRange.length - 1];
    fetchData(startDate, endDate);
  }
};

const selectSingleProduct = (product) => {
  selectedProducts.value = [product];
};

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
    const productsResponse = await apiClient.get('/products_list');
    products.value = productsResponse.data;
    if (products.value.length > 0) {
      selectedProducts.value = [...products.value];
    }
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

.list-container {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
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
  min-width: 250px;
  max-width: 250px;
  margin-top: 0;
}
</style>