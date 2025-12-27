# Terraform outputs

output "ydb_endpoint" {
  description = "YDB database endpoint"
  value       = yandex_ydb_database_serverless.main.ydb_full_endpoint
}

output "ydb_database" {
  description = "YDB database path"
  value       = yandex_ydb_database_serverless.main.database_path
}

output "queue_url" {
  description = "Message Queue URL"
  value       = yandex_message_queue.tasks_queue.id
  sensitive   = true
}

output "bucket_name" {
  description = "Object Storage bucket name"
  value       = yandex_storage_bucket.main.bucket
}

output "registry_id" {
  description = "Container Registry ID"
  value       = yandex_container_registry.main.id
}

output "functions_sa_id" {
  description = "Functions Service Account ID"
  value       = yandex_iam_service_account.functions_sa.id
  sensitive   = true
}

output "worker_sa_id" {
  description = "Worker Service Account ID"
  value       = yandex_iam_service_account.worker_sa.id
  sensitive   = true
}

output "create_task_function_id" {
  description = "Create Task Function ID"
  value       = yandex_function.create_task.id
}

output "list_tasks_function_id" {
  description = "List Tasks Function ID"
  value       = yandex_function.list_tasks.id
}

output "static_pages_function_id" {
  description = "Static Pages Function ID"
  value       = yandex_function.static_pages.id
}

output "create_task_function_url" {
  description = "Create Task Function URL (API endpoint)"
  value       = "https://functions.yandexcloud.net/${yandex_function.create_task.id}"
}

output "list_tasks_function_url" {
  description = "List Tasks Function URL (API endpoint)"
  value       = "https://functions.yandexcloud.net/${yandex_function.list_tasks.id}"
}

output "static_pages_function_url" {
  description = "Static Pages Function URL - OPEN THIS IN BROWSER"
  value       = "https://functions.yandexcloud.net/${yandex_function.static_pages.id}"
}

output "aws_access_key_id" {
  description = "AWS Access Key ID for Functions (used in environment variables)"
  value       = yandex_iam_service_account_static_access_key.functions_sa_key.access_key
  sensitive   = true
}

output "aws_secret_access_key" {
  description = "AWS Secret Access Key for Functions (used in environment variables)"
  value       = yandex_iam_service_account_static_access_key.functions_sa_key.secret_key
  sensitive   = true
}

output "yandex_api_key" {
  description = "Yandex API Key for Worker (YandexGPT and SpeechKit)"
  value       = yandex_iam_service_account_api_key.worker_api_key.secret_key
  sensitive   = true
}

# Lockbox outputs removed - using IAM tokens from metadata service instead
# output "lockbox_secret_id" {
#   description = "Lockbox Secret ID for API keys"
#   value       = yandex_lockbox_secret.api_keys.id
#   sensitive   = true
# }

output "worker_container_id" {
  description = "Worker Serverless Container ID"
  value       = yandex_serverless_container.worker.id
}

output "worker_trigger_id" {
  description = "Worker Trigger ID"
  value       = yandex_function_trigger.worker_trigger.id
}

output "worker_image_url" {
  description = "Worker Container Image URL"
  value       = "cr.yandex/${yandex_container_registry.main.id}/worker:latest"
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = yandex_api_gateway.main.id
}

output "api_gateway_domain" {
  description = "API Gateway domain (HTTPS endpoint)"
  value       = yandex_api_gateway.main.domain
}

output "api_gateway_url" {
  description = "API Gateway URL - OPEN THIS IN BROWSER (HTTPS only)"
  value       = "https://${yandex_api_gateway.main.domain}"
}

# Summary output for easy access
output "deployment_summary" {
  description = "Deployment summary with key information"
  value = {
    api_gateway_url   = "https://${yandex_api_gateway.main.domain}"
    web_interface_url = "https://${yandex_api_gateway.main.domain}"
    ydb_endpoint      = yandex_ydb_database_serverless.main.ydb_full_endpoint
    ydb_database      = yandex_ydb_database_serverless.main.database_path
    bucket_name       = yandex_storage_bucket.main.bucket
    region            = "ru-central1"
    worker_container  = yandex_serverless_container.worker.id
  }
}
