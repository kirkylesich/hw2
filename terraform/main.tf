terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "0.175.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.0"
}

# Provider configuration using YC_TOKEN environment variable
provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = var.zone
}

# Docker provider for building images
provider "docker" {
  registry_auth {
    address  = "cr.yandex"
    username = "oauth"
    password = var.yc_token
  }
}

# Random suffix for unique bucket name
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Service Account for Cloud Functions
resource "yandex_iam_service_account" "functions_sa" {
  name        = "${var.prefix}-functions-sa"
  description = "Service account for Cloud Functions"
}

# Service Account for Worker Container
resource "yandex_iam_service_account" "worker_sa" {
  name        = "${var.prefix}-worker-sa"
  description = "Service account for Worker Container"
}

# IAM roles for Functions SA
resource "yandex_resourcemanager_folder_iam_member" "functions_ydb_editor" {
  folder_id = var.folder_id
  role      = "ydb.editor"
  member    = "serviceAccount:${yandex_iam_service_account.functions_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "functions_ymq_writer" {
  folder_id = var.folder_id
  role      = "ymq.writer"
  member    = "serviceAccount:${yandex_iam_service_account.functions_sa.id}"
}

# IAM roles for Worker SA
resource "yandex_resourcemanager_folder_iam_member" "worker_ydb_editor" {
  folder_id = var.folder_id
  role      = "ydb.editor"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_ymq_reader" {
  folder_id = var.folder_id
  role      = "ymq.reader"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_ymq_writer" {
  folder_id = var.folder_id
  role      = "ymq.writer"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_storage_editor" {
  folder_id = var.folder_id
  role      = "storage.editor"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_ai_languagemodels_user" {
  folder_id = var.folder_id
  role      = "ai.languageModels.user"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_ai_speechkit_stt_user" {
  folder_id = var.folder_id
  role      = "ai.speechkit-stt.user"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "worker_invoker" {
  folder_id = var.folder_id
  role      = "serverless.containers.invoker"
  member    = "serviceAccount:${yandex_iam_service_account.worker_sa.id}"
}

# YDB Database (Serverless)
resource "yandex_ydb_database_serverless" "main" {
  name      = "${var.prefix}-db"
  folder_id = var.folder_id
}

# Message Queue (Standard)
resource "yandex_message_queue" "tasks_queue" {
  name                       = "${var.prefix}-tasks-queue"
  visibility_timeout_seconds = 900    # 15 minutes
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling

  access_key = yandex_iam_service_account_static_access_key.functions_sa_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.functions_sa_key.secret_key

  lifecycle {
    create_before_destroy = false
  }

  depends_on = [
    yandex_resourcemanager_folder_iam_member.functions_ymq_admin,
    yandex_resourcemanager_folder_iam_member.functions_ymq_writer
  ]
}

# Object Storage Bucket
resource "yandex_storage_bucket" "main" {
  bucket        = "${var.prefix}-storage-${random_string.bucket_suffix.result}"
  access_key    = yandex_iam_service_account_static_access_key.functions_sa_key.access_key
  secret_key    = yandex_iam_service_account_static_access_key.functions_sa_key.secret_key
  force_destroy = true

  anonymous_access_flags {
    read = true
    list = false
  }

  lifecycle {
    create_before_destroy = false
  }

  depends_on = [
    yandex_iam_service_account_static_access_key.functions_sa_key,
    yandex_resourcemanager_folder_iam_member.functions_storage_editor
  ]
}

# Static Access Keys for Functions Service Account
resource "yandex_iam_service_account_static_access_key" "functions_sa_key" {
  service_account_id = yandex_iam_service_account.functions_sa.id
  description        = "Static access key for Cloud Functions to access S3 and SQS"
}

# IAM roles for Functions SA - add storage.editor for S3 bucket creation
resource "yandex_resourcemanager_folder_iam_member" "functions_storage_editor" {
  folder_id = var.folder_id
  role      = "storage.editor"
  member    = "serviceAccount:${yandex_iam_service_account.functions_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "functions_ymq_admin" {
  folder_id = var.folder_id
  role      = "ymq.admin"
  member    = "serviceAccount:${yandex_iam_service_account.functions_sa.id}"
}

# Archive Python functions
data "archive_file" "create_task_function" {
  type        = "zip"
  source_dir  = "${path.module}/../python_functions/create_task"
  output_path = "${path.module}/.terraform/create_task.zip"
}

data "archive_file" "list_tasks_function" {
  type        = "zip"
  source_dir  = "${path.module}/../python_functions/list_tasks"
  output_path = "${path.module}/.terraform/list_tasks.zip"
}

data "archive_file" "static_pages_function" {
  type        = "zip"
  source_dir  = "${path.module}/../python_functions/static_pages"
  output_path = "${path.module}/.terraform/static_pages.zip"
}

# Cloud Function: Create Task
resource "yandex_function" "create_task" {
  name               = "${var.prefix}-create-task"
  user_hash          = data.archive_file.create_task_function.output_base64sha256
  runtime            = "python312"
  entrypoint         = "index.handler"
  memory             = 256
  execution_timeout  = "30"
  service_account_id = yandex_iam_service_account.functions_sa.id

  environment = {
    YDB_ENDPOINT          = yandex_ydb_database_serverless.main.ydb_full_endpoint
    YDB_DATABASE          = yandex_ydb_database_serverless.main.database_path
    MQ_QUEUE_URL          = yandex_message_queue.tasks_queue.id
    MQ_ENDPOINT           = "https://message-queue.api.cloud.yandex.net"
    AWS_REGION            = "ru-central1"
    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.functions_sa_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.functions_sa_key.secret_key
  }

  content {
    zip_filename = data.archive_file.create_task_function.output_path
  }
}

# Allow unauthenticated invoke for create_task
resource "yandex_function_iam_binding" "create_task_public" {
  function_id = yandex_function.create_task.id
  role        = "functions.functionInvoker"
  members     = ["system:allUsers"]
}

# Cloud Function: List Tasks
resource "yandex_function" "list_tasks" {
  name               = "${var.prefix}-list-tasks"
  user_hash          = data.archive_file.list_tasks_function.output_base64sha256
  runtime            = "python312"
  entrypoint         = "index.handler"
  memory             = 256
  execution_timeout  = "30"
  service_account_id = yandex_iam_service_account.functions_sa.id

  environment = {
    YDB_ENDPOINT          = yandex_ydb_database_serverless.main.ydb_full_endpoint
    YDB_DATABASE          = yandex_ydb_database_serverless.main.database_path
    S3_BUCKET             = yandex_storage_bucket.main.bucket
    S3_ENDPOINT           = "https://storage.yandexcloud.net"
    AWS_REGION            = "ru-central1"
    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.functions_sa_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.functions_sa_key.secret_key
  }

  content {
    zip_filename = data.archive_file.list_tasks_function.output_path
  }

  depends_on = [
    yandex_storage_bucket.main
  ]

  lifecycle {
    replace_triggered_by = [
      yandex_storage_bucket.main
    ]
  }
}

# Allow unauthenticated invoke for list_tasks
resource "yandex_function_iam_binding" "list_tasks_public" {
  function_id = yandex_function.list_tasks.id
  role        = "functions.functionInvoker"
  members     = ["system:allUsers"]
}

# Cloud Function: Static Pages
resource "yandex_function" "static_pages" {
  name               = "${var.prefix}-static-pages"
  user_hash          = data.archive_file.static_pages_function.output_base64sha256
  runtime            = "python312"
  entrypoint         = "index.handler"
  memory             = 128
  execution_timeout  = "10"
  service_account_id = yandex_iam_service_account.functions_sa.id

  content {
    zip_filename = data.archive_file.static_pages_function.output_path
  }
}

# Allow unauthenticated invoke for static_pages
resource "yandex_function_iam_binding" "static_pages_public" {
  function_id = yandex_function.static_pages.id
  role        = "functions.functionInvoker"
  members     = ["system:allUsers"]
}

# Container Registry
resource "yandex_container_registry" "main" {
  name      = "${var.prefix}-registry"
  folder_id = var.folder_id

  lifecycle {
    create_before_destroy = false
  }
}

# Grant worker SA permission to pull images from registry
resource "yandex_container_registry_iam_binding" "worker_puller" {
  registry_id = yandex_container_registry.main.id
  role        = "container-registry.images.puller"
  members     = ["serviceAccount:${yandex_iam_service_account.worker_sa.id}"]
}

# Build and push Docker image
resource "docker_image" "worker" {
  name = "cr.yandex/${yandex_container_registry.main.id}/worker:latest"
  
  build {
    context    = "${path.module}/.."
    dockerfile = "Dockerfile.worker"
    platform   = "linux/amd64"
  }
  
  depends_on = [yandex_container_registry.main]
}

resource "docker_registry_image" "worker" {
  name          = docker_image.worker.name
  keep_remotely = false

  depends_on = [
    docker_image.worker,
    yandex_container_registry_iam_binding.worker_puller
  ]
}

resource "null_resource" "cleanup_registry" {
  triggers = {
    registry_id = yandex_container_registry.main.id
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      IMAGE_IDS=$(yc container image list --registry-id ${self.triggers.registry_id} --format json 2>/dev/null | jq -r '.[].id' 2>/dev/null | tr '\n' ' ')
      if [ -n "$IMAGE_IDS" ]; then
        yc container image delete $IMAGE_IDS 2>/dev/null || true
      fi
    EOT
  }

  depends_on = [
    docker_registry_image.worker,
    yandex_serverless_container.worker
  ]
}

# Static Access Keys for Worker Service Account
resource "yandex_iam_service_account_static_access_key" "worker_sa_key" {
  service_account_id = yandex_iam_service_account.worker_sa.id
  description        = "Static access key for Worker Container to access S3 and SQS"
}

# API Key for Worker Service Account (for YandexGPT and SpeechKit)
resource "yandex_iam_service_account_api_key" "worker_api_key" {
  service_account_id = yandex_iam_service_account.worker_sa.id
  description        = "API key for YandexGPT and SpeechKit access"
}

resource "yandex_serverless_container" "worker" {
  name               = "${var.prefix}-worker"
  folder_id          = var.folder_id
  service_account_id = yandex_iam_service_account.worker_sa.id
  memory             = 2048   # 2GB for video processing
  execution_timeout  = "900s" # 15 minutes (maximum allowed)
  concurrency        = 2      # Process up to 2 requests per container instance

  image {
    url = docker_registry_image.worker.name

    environment = {
      YDB_ENDPOINT          = yandex_ydb_database_serverless.main.ydb_full_endpoint
      YDB_DATABASE          = yandex_ydb_database_serverless.main.database_path
      MQ_QUEUE_URL          = yandex_message_queue.tasks_queue.id
      MQ_ENDPOINT           = "https://message-queue.api.cloud.yandex.net"
      AWS_REGION            = "ru-central1"
      AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.worker_sa_key.access_key
      AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.worker_sa_key.secret_key
      S3_BUCKET             = yandex_storage_bucket.main.bucket
      S3_ENDPOINT           = "https://storage.yandexcloud.net"
      FOLDER_ID             = var.folder_id
      YANDEX_API_KEY        = yandex_iam_service_account_api_key.worker_api_key.secret_key
    }
  }

  depends_on = [
    docker_registry_image.worker,
    yandex_container_registry_iam_binding.worker_puller,
    yandex_storage_bucket.main
  ]

  lifecycle {
    replace_triggered_by = [
      yandex_storage_bucket.main
    ]
    create_before_destroy = false
  }
}

# Trigger for Worker Container (invoke on queue messages)
resource "yandex_function_trigger" "worker_trigger" {
  name        = "${var.prefix}-worker-trigger"
  folder_id   = var.folder_id
  description = "Trigger worker container on new messages in queue"

  message_queue {
    queue_id           = yandex_message_queue.tasks_queue.arn
    service_account_id = yandex_iam_service_account.worker_sa.id
    batch_size         = 1
    batch_cutoff       = 0  # Process immediately, don't wait
  }

  container {
    id                 = yandex_serverless_container.worker.id
    service_account_id = yandex_iam_service_account.worker_sa.id
  }

  depends_on = [
    yandex_serverless_container.worker,
    yandex_message_queue.tasks_queue
  ]

  lifecycle {
    create_before_destroy = false
  }
}

# API Gateway
resource "yandex_api_gateway" "main" {
  name        = "${var.prefix}-api-gateway"
  folder_id   = var.folder_id
  description = "API Gateway for Lecture Notes Generator"

  spec = templatefile("${path.module}/api_gateway_spec.yaml", {
    static_pages_function_id = yandex_function.static_pages.id
    list_tasks_function_id   = yandex_function.list_tasks.id
    create_task_function_id  = yandex_function.create_task.id
    functions_sa_id          = yandex_iam_service_account.functions_sa.id
  })

  depends_on = [
    yandex_function.static_pages,
    yandex_function.list_tasks,
    yandex_function.create_task
  ]
}
