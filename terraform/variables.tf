variable "project_id" {
  description = "GCP Project that hosts the project"
  type        = string
  default     = "credit-risk-dev-00215"
}

variable "region" {
  description = "Johannesburg reegion, used for BigQuery and later for Cloud Run"
  type        = string
  default     = "africa-south1"
}