# customer-sentiment-tracking-service

## Запуск проекта
В `docker-compose.yml` в сервисе `vllm` можно изменить параметр `gpu-memory-utilization` от 0.5 до 1.0 для оптимизации использования GPU.

Для запуска проекта выполните команду:
```bash
docker-compose up --build
```