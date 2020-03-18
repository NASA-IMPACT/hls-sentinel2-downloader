resource "aws_ecr_repository" "downloader" {
  name = "${terraform.workspace}-downloader"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.downloader.repository_url
}
