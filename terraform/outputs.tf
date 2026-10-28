output "dataset_ids" {
  description = "BigQuery datasets created for each layer"
  value       = [for d in google_bigquery_dataset.layers : d.dataset_id]
}

output "pipeline_service_account_email" {
  description = "Service account used by the pipeline"
  value       = google_service_account.pipeline.email
}