resource "aws_ecr_repository" "downloader" {
  name = "${terraform.workspace}-downloader"
}
