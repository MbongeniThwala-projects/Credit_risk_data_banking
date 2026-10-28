#APIs that we needs

locals {
  apis = [
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# BQ datasets, one per layer
locals {
  datasets = {
    raw     = "Raw loan book, repayment events and reference data exactly as generated"
    staging = "Cleaned and typed models (dbt staging layer)"
    marts   = "Credit risk models"
  }
}

resource "google_bigquery_dataset" "layers" {
  for_each      = local.datasets
  dataset_id    = each.key
  friendly_name = each.key
  description   = each.value
  location      = var.region

  labels = {
    project = "credit-risk"
    env     = "dev"
  }

  #lets terraform destroy, remove the datasets even if it has tables
  delete_contents_on_destroy = true
  depends_on                 = [google_project_service.apis]
}

# service account with least privilege access
resource "google_service_account" "pipeline" {
  account_id   = "pipeline-runner"
  display_name = "Credit risk pipeline runner (loads and dbt)"

  depends_on = [google_project_service.apis]
}

#Permission to run to run BQ jobs (queries and load jobs) in the project
resource "google_project_iam_member" "pipeline_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# permission to read and write tables, granted per dataser and not project-wide
resource "google_bigquery_dataset_iam_member" "pipeline_editor" {
  for_each   = google_bigquery_dataset.layers
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline.email}"
}