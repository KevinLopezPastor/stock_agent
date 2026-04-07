variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "langfuse_public_key" {
  type      = string
  sensitive = true
}

variable "langfuse_secret_key" {
  type      = string
  sensitive = true
}

variable "langfuse_base_url" {
  type = string
}
