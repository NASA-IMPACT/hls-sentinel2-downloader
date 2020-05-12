resource "aws_s3_bucket" "upload_bucket" {
  bucket_prefix = "${var.project_prefix}-uploads-"
}
