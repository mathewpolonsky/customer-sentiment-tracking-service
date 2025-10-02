# customer-sentiment-tracking-service

## Запуск проекта
В `docker-compose.yml` в сервисе `vllm` можно изменить параметр `gpu-memory-utilization` для оптимизации использования GPU. Сейчас он установлен на 0.5.

Для запуска проекта выполните команду:
```bash
docker-compose up --build
```