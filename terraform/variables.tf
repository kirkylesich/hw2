# Terraform variables for Yandex Cloud deployment

variable "cloud_id" {
  description = "Yandex Cloud ID"
  type        = string
}

variable "folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}

variable "prefix" {
  description = "Prefix for all resource names (pattern: prefix-name)"
  type        = string
  default     = "lecture-notes"
}

variable "zone" {
  description = "Yandex Cloud availability zone"
  type        = string
  default     = "ru-central1-a"
}

variable "speechkit_api_key" {
  description = "API key for Yandex SpeechKit (optional, can be set in Lockbox console)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "yandexgpt_api_key" {
  description = "API key for YandexGPT (optional, can be set in Lockbox console)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "yc_token" {
  description = "Yandex Cloud OAuth token for Docker registry authentication"
  type        = string
  sensitive   = true
}
