output "dataset_ids" {
  description = "BigQuery datasets created for each layer"
  value       = [for d in google_bigquery_dataset.layers : d.dataset_id]
}

output "pipeline_service_account_email" {
  description = "Service account used by the pipeline"
  value       = google_service_account.pipeline.email
}

output "landing_bucket" {
  description = "Cloud Storage bucket for raw extracts"
  value       = google_storage_bucket.landing.name
}