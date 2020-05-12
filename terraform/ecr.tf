resource "aws_ecr_repository" "downloader" {
  name = "${var.project_prefix}-downloader"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.downloader.repository_url
}
