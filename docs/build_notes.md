This is a GCP project, so its IAM, billing and cleanup are isolated from other work and it can be rebuilt or destroyed independently.

We will use Terraform:
-> Infrastructure as code makes the project reproducible:
    anyone can rebuild it from the repo, and 'terraform destroy' removes it cleanly when the trial ends (using the free GCP). Everything is placed in `africa-south1` (Johannesburg). For real banking data, the project uses this region as its default. Datasets are split into raw, staging and marts layers so that each stage of the pipeline has a clear purpose. The pipeline service account gets only the roles it needs, with table access granted per dataset instead of project-wide, following least privilege.