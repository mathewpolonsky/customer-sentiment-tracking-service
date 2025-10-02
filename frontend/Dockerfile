FROM node:24.8-alpine

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем package.json и package-lock.json для установки зависимостей
COPY package*.json ./
RUN npm install

# Копируем остальной код приложения
COPY . .

# Проекты Vuetify по умолчанию запускаются на порту 3000
EXPOSE 3000

CMD ["npm", "run", "dev"]